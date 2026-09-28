import os
import re
import sys
import json
import urllib.parse
import requests
from bs4 import BeautifulSoup

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SETTING_FILE = os.path.join(WORKSPACE_ROOT, "setting", "contents_set_url.md")
COOKIE_FILE = os.path.join(WORKSPACE_ROOT, "setting", "lcdms_cookie.txt")
INPUT_DIR = os.path.join(WORKSPACE_ROOT, "input")
MEDIA_DIR = os.path.join(INPUT_DIR, "media")

def load_subject_urls():
    if not os.path.exists(SETTING_FILE):
        return {}
    mapping = {}
    with open(SETTING_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("-"):
                continue
            match = re.match(r"^-\s*([^:]+)\s*:\s*(https?://[^\s]+)", line)
            if match:
                mapping[match.group(1).strip()] = match.group(2).strip()
    return mapping

def load_cookies():
    cookies = {}
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            raw = f.read().replace("\n", " ").strip()
            for item in raw.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookies[k.strip()] = v.strip()
    return cookies

def js_escape_encode(s: str) -> str:
    return urllib.parse.quote(urllib.parse.quote(s, safe="-_.!~*'()"), safe="*+-./@")

def init_session(cookies: dict) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Referer": "https://home.iscu.ac.kr/cdms/index.jsp",
    })
    session.cookies.update(cookies)
    session.post("https://home.iscu.ac.kr/cdms/login/login.scu", data={"p": ""}, timeout=10)
    return session

def parse_contents_seqno(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    params = urllib.parse.parse_qs(parsed.query)
    return params.get("contents_seqno", [""])[0]

def parse_final_sb_download(html_text: str):
    """
    최종SB 상세 HTML에서 [최종첨부파일] 영역의 fileDownload 함수 인자만 정밀 추출
    """
    soup = BeautifulSoup(html_text, "html.parser")
    for th in soup.find_all(["th", "td"]):
        if "최종첨부파일" in th.get_text():
            target_td = th.find_next_sibling("td")
            if target_td:
                td_html = str(target_td)
                m = re.search(r"fileDownload\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'", td_html)
                if m:
                    return {
                        "org_file": m.group(1).strip(),
                        "down_file": m.group(2).strip(),
                        "attach_path": m.group(3).strip()
                    }
    
    pos = html_text.find("최종첨부파일")
    if pos != -1:
        sub = html_text[pos:pos+1500]
        m = re.search(r"fileDownload\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'", sub)
        if m:
            return {
                "org_file": m.group(1).strip(),
                "down_file": m.group(2).strip(),
                "attach_path": m.group(3).strip()
            }
    return None

def download_file(session: requests.Session, url: str, dest_path: str, chunk_size: int = 65536):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        print(f"    -> [기존 파일 존재 (재사용)]: {os.path.basename(dest_path)} ({os.path.getsize(dest_path):,} bytes)")
        return True, os.path.getsize(dest_path)

    r = session.get(url, stream=True, timeout=120)
    if r.status_code == 200:
        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
        return True, downloaded
    return False, 0

def fetch_week_data(subject: str, week: int):
    mapping = load_subject_urls()
    if subject not in mapping:
        print(f"[오류] 'setting/contents_set_url.md'에 '{subject}' 과목이 없습니다.")
        return None

    base_url = mapping[subject]
    contents_seqno = parse_contents_seqno(base_url)
    cookies = load_cookies()
    if not cookies:
        print("[오류] 'setting/lcdms_cookie.txt' 쿠키 파일이 비어있습니다.")
        return None

    session = init_session(cookies)
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)

    print("\n" + "="*60)
    print(f"[*] LCDMS 최종SB 및 미디어 수집기 (Read-Only 모드)")
    print(f"[*] 과목명: {subject} (콘텐츠번호: {contents_seqno}), 주차: {week}주차")
    print("="*60)

    # 1. 주차 메타데이터 조회
    api_url = "https://home.iscu.ac.kr/cdms/progress/devstatu/devstatuDetailS.scu"
    try:
        resp = session.post(api_url, data={"contents_seqno": contents_seqno}, timeout=15)
        meta_data = resp.json()
        result_list = meta_data.get("resultList", [])
    except Exception as e:
        print(f"[오류] 메타데이터 조회 실패: {e}")
        return None

    target_week = None
    for row in result_list:
        w = row.get("seq") or row.get("weekNo")
        if str(w) == str(week):
            target_week = row
            break

    if not target_week:
        print(f"[오류] {week}주차 데이터를 시스템에서 찾을 수 없습니다.")
        return None

    ws_seqno = target_week.get("wsSeqno")

    # 단계 탐색: 최종SB (0416), 미디어 (0406 또는 0434)
    sb_stage = None
    media_stage = None

    for i in range(1, 26):
        cd = target_week.get(f"s{i}WsStageCd")
        if cd == "0416":
            sb_stage = {
                "stage_num": target_week.get(f"s{i}StageNum") or i,
                "seqno": target_week.get(f"s{i}Seqno"),
                "name": target_week.get(f"s{i}WsStageCdNm", "최종SB")
            }
        elif cd in ["0406", "0434"]:
            media_stage = {
                "stage_num": target_week.get(f"s{i}StageNum") or i,
                "seqno": target_week.get(f"s{i}Seqno"),
                "name": target_week.get(f"s{i}WsStageCdNm", "미디어")
            }

    # 2. 최종SB 다운로드
    sb_downloaded_path = None
    if sb_stage and sb_stage["seqno"]:
        detail_url = (
            f"https://home.iscu.ac.kr/cdms/progress/devstatu/devstatuStepCommonDetail.scu"
            f"?contents_seqno={contents_seqno}&ws_seqno={ws_seqno}&stage_num={sb_stage['stage_num']}&seqno={sb_stage['seqno']}&weekNo={week}"
        )
        try:
            r_sb = session.get(detail_url, timeout=15)
            r_sb.encoding = "utf-8"
            sb_info = parse_final_sb_download(r_sb.text)
            if sb_info:
                down_url = (
                    f"https://home.iscu.ac.kr/cdms/userDown.scu"
                    f"?cmd=contents&filepath={sb_info['attach_path']}&filename={js_escape_encode(sb_info['down_file'])}&orgfilename={js_escape_encode(sb_info['org_file'])}"
                )
                dest = os.path.join(INPUT_DIR, sb_info["org_file"])
                print(f"[+] 최종SB 발견: {sb_info['org_file']}")
                ok, size = download_file(session, down_url, dest)
                if ok:
                    print(f"    -> [수집 완료] {dest} ({size:,} bytes)")
                    sb_downloaded_path = dest
                else:
                    print(f"    -> [수집 실패]")
            else:
                print(f"[-] 최종SB 상세 페이지에서 '최종첨부파일'을 찾을 수 없습니다.")
        except Exception as e:
            print(f"[오류] 최종SB 수집 중 에러: {e}")
    else:
        print(f"[-] {week}주차에 최종SB(0416) 단계가 설정되어 있지 않습니다.")

    # 3. 미디어 단계 비디오 목록 수집 및 다운로드 (stepmakeMediaListL.scu API)
    media_downloaded_list = []
    if media_stage and media_stage["seqno"]:
        media_api_url = "https://home.iscu.ac.kr/cdms/progress/stepmake/stepmakeMediaListL.scu"
        try:
            r_media = session.post(media_api_url, data={
                "contents_seqno": contents_seqno,
                "seqno": media_stage["seqno"],
                "ws_seqno": ws_seqno
            }, timeout=15)
            media_data = r_media.json()
            video_items = media_data.get("resultList", [])

            if video_items:
                print(f"\n[+] 미디어 동영상 {len(video_items)}개 클립 발견:")
                # 파일명 순서대로 정렬 (10_01.mp4, 10_02.mp4 ...)
                video_items.sort(key=lambda x: x.get("fileName", ""))
                for idx, item in enumerate(video_items, 1):
                    v_name = item.get("fileName")
                    v_url = (item.get("fullFilePath") or "") + v_name
                    run_time = item.get("runTime", 0)
                    mm, ss = divmod(run_time, 60)
                    dest = os.path.join(MEDIA_DIR, v_name)
                    print(f"    [{idx:02d}/{len(video_items):02d}] {v_name} (길이: {mm:02d}:{ss:02d}) 다운로드 중...")
                    ok, size = download_file(session, v_url, dest)
                    if ok:
                        print(f"         -> 완료 ({size:,} bytes)")
                        media_downloaded_list.append(dest)
                    else:
                        print(f"         -> 실패 (URL: {v_url})")
            else:
                print(f"[-] 미디어 단계에 등록된 동영상이 없습니다.")
        except Exception as e:
            print(f"[오류] 미디어 목록 조회 중 에러: {e}")
    else:
        print(f"[-] {week}주차에 미디어 단계가 설정되어 있지 않습니다.")

    return {
        "final_sb": sb_downloaded_path,
        "media_videos": media_downloaded_list
    }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python lcdms_downloader.py <과목명> <주차>")
        print("예시: python lcdms_downloader.py 고양이관리학 10")
    else:
        subj = sys.argv[1]
        wk = int(sys.argv[2].replace("주차", "").replace("주", ""))
        fetch_week_data(subj, wk)
