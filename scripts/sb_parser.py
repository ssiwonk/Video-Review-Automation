import os
import re
import sys
from pptx import Presentation

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def is_header_slide(slide) -> bool:
    """
    슬라이드 내에 과목명, 주차명, 페이지번호 등 표준 프레임 헤더 키워드가 있는지 검사
    """
    text_corpus = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                text_corpus.append(p.text.strip())
    
    full_text = " ".join(text_corpus)
    # 헤더 프레임 특징: '과목명', '주차명', '페이지번호' 또는 '0X_0X_0X' 형식
    has_subject = "과목명" in full_text
    has_week = "주차명" in full_text
    has_page_no = "페이지번호" in full_text or bool(re.search(r"\d{2}_\d{2}_\d{2}", full_text))
    
    # 2개 이상 매칭되면 헤더/프레임 페이지로 판단
    matches = sum([has_subject, has_week, has_page_no])
    return matches >= 2

def extract_video_filename(slide) -> str:
    """
    프레임 슬라이드에서 동영상 파일명(예: 19531905_10_01.mp4 또는 *.mp4) 추출
    """
    for shape in slide.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                txt = p.text.strip()
                m = re.search(r"([a-zA-Z0-9_]+\.mp4)", txt)
                if m:
                    return m.group(1)
    return ""

def parse_sb_pptx(pptx_path: str):
    """
    최종SB PPTX를 분석하여 동영상별 강의 슬라이드 목록 및 예상 카운터 범위 매핑
    """
    prs = Presentation(pptx_path)
    total_slides = len(prs.slides)
    print(f"[*] 총 슬라이드 수: {total_slides}장")

    video_groups = []
    current_video = None
    global_counter = 1  # 주차 전체 기준 연속 카운터

    for idx, slide in enumerate(prs.slides, 1):
        is_header = is_header_slide(slide)
        if is_header:
            v_name = extract_video_filename(slide)
            if v_name or "동영상" in str(idx):
                # 새로운 동영상 섹션 시작
                current_video = {
                    "video_file": v_name,
                    "frame_slide_num": idx,
                    "slides": [],
                    "start_counter": global_counter,
                    "end_counter": global_counter
                }
                video_groups.append(current_video)
        else:
            # 헤더가 없는 실제 강의 슬라이드
            slide_info = {
                "slide_num": idx,
                "expected_counter": global_counter
            }
            if current_video is not None:
                current_video["slides"].append(slide_info)
                current_video["end_counter"] = global_counter
            else:
                # 첫 동영상 헤더 이전의 슬라이드가 있다면 기본 그룹 생성
                if not video_groups:
                    current_video = {
                        "video_file": "default_clip",
                        "frame_slide_num": 0,
                        "slides": [],
                        "start_counter": global_counter,
                        "end_counter": global_counter
                    }
                    video_groups.append(current_video)
                current_video["slides"].append(slide_info)
                current_video["end_counter"] = global_counter

            global_counter += 1

    # 요약 출력
    print("\n" + "="*50)
    print("[*] SB 슬라이드 구조 분석 결과")
    print("="*50)
    for i, grp in enumerate(video_groups, 1):
        v_label = grp["video_file"] if grp["video_file"] else f"영상_{i}"
        s_count = len(grp["slides"])
        if s_count > 0:
            print(f"[{i}] {v_label}: 슬라이드 {s_count}장 (예상 카운터: {grp['start_counter']} ~ {grp['end_counter']})")
        else:
            print(f"[{i}] {v_label}: 연결된 강의 슬라이드 없음")

    return video_groups

if __name__ == "__main__":
    if len(sys.argv) > 1:
        parse_sb_pptx(sys.argv[1])
    else:
        print("사용법: python sb_parser.py <pptx_path>")
