# 🎬 [SCU 콘텐츠 품질 보증] 최종SB ↔ 동영상 자동 대조·검수 시스템
> **Video-Review-Automation**: 서울사이버대학교(SCU) 교육 콘텐츠의 최종 스토리보드(PPTX)와 실제 송출용 동영상(MP4)을 대조하여, 슬라이드의 누락 및 순서 오류를 100% 자동 검출하는 지능형 검수 솔루션입니다.

---

## ⚡ 1. 30초 핵심 요약

* **기존**: 수십~수백 장의 PPTX 슬라이드와 1시간이 넘는 동영상을 일일이 재생하며 화면을 눈으로 대조 (주차당 1~2시간 소요, 미세한 슬라이드 누락 빈번)
* **도입 후**: 대화창에 **"고양이관리학 10주차 검수해줘"** (또는 단 한 줄 명령어 실행) 시, **LCDMS 자동 수집 ➔ SB 구조 분석 ➔ 시계열 컨택트시트 생성 ➔ 종합 검수 보고서 발행**까지 **원클릭 자동 완료**

---

## 🛠️ 2. 사전 환경 설치 (최초 1회)

본 시스템은 Python 3.10 이상 환경에서 동작합니다.

```powershell
pip install -r requirements.txt
```

---

## ⚙️ 3. 사전 설정 (단 2가지만 확인)

### ① 과목 URL 등록 (`setting/contents_set_url.md`)
검수하려는 과목의 LCDMS 개발현황 페이지 URL을 등록합니다:
```markdown
- 고양이관리학 : https://home.iscu.ac.kr/cdms/progress/devstatu/devstatuDetailSView.scu?contents_seqno=174508...
- 골프트레이닝 : https://home.iscu.ac.kr/cdms/progress/devstatu/devstatuDetailSView.scu?contents_seqno=174509...
- 머신러닝 : https://home.iscu.ac.kr/cdms/progress/devstatu/devstatuDetailSView.scu?contents_seqno=173620...
```

### ② 로그인 세션 쿠키 등록 (`setting/lcdms_cookie.txt`)
1. 웹 브라우저(Chrome/Edge 등)에서 LCDMS에 로그인합니다.
2. `F12(개발자 도구)` ➔ `Application(애플리케이션)` 탭 ➔ 좌측 `Cookies` ➔ `https://home.iscu.ac.kr` 클릭
3. `tongken` 항목의 Value 값을 복사하여 `setting/lcdms_cookie.txt`에 저장합니다. (형식: `tongken=53ed4dac...`)
*(※ 쿠키 만료 알림이 뜨면 위 방법으로 최신 값만 갱신해 넣으면 됩니다.)*

---

## 🚀 4. 실무 사용법 (단 한 줄 실행)

### 방법 A. AI 에이전트 대화창에서 요청 (가장 간편함)
* 대화창에 과목명과 주차를 말씀해 주세요:
  > **"고양이관리학 10주차 검수해줘"**  
  > **"머신러닝 9주차 최종SB랑 동영상 비교해줘"**

### 방법 B. 터미널(CLI) 직접 실행
```powershell
python scripts/run_review.py 고양이관리학 10
```

---

## 📂 5. 프로젝트 폴더 구조

```text
Video-Review-Automation/
├── setting/
│   ├── contents_set_url.md      # 검수 과목 URL 목록
│   ├── lcdms_cookie.txt         # LCDMS tongken 세션 쿠키
│   └── aside-setting/           # 원본 분석 로직 참조 문서
├── input/                       # 자동 수집된 임시 작업 폴더 (.gitignore 대상)
│   ├── SB_과목명_주차_최종.pptx # 최종첨부파일 단독 수집
│   └── media/                   # 분할 동영상 MP4 파일들
├── output/                      # 최종 산출물 폴더
│   ├── reports/                 # 발행된 종합 검수 보고서 (.md)
│   └── captures/                # 시계열 타임코드 컨택트시트 캡처 (.jpg)
├── scripts/                     # 프로덕션 핵심 파이프라인
│   ├── lcdms_downloader.py      # LCDMS 안전 수집기 (엄격한 Read-Only)
│   ├── sb_parser.py             # PPTX 슬라이드 및 동영상 매핑 분석기
│   ├── video_analyzer.py        # 시계열 컨택트시트 및 화면 분석 엔진
│   └── run_review.py            # 원클릭 통합 실행기 (Entry Point)
├── requirements.txt             # 파이썬 의존성 패키지 목록
├── .gitignore                   # 대용량 미디어 및 임시 파일 제외 설정
└── README.md                    # 본 사용자 매뉴얼
```

---

## 📊 6. 산출물 예시 (`output/reports/`)

발행되는 종합 검수 보고서(`검수보고서_[과목명]_[주차].md`)는 다음 구성으로 자동 발행됩니다:

1. **🎯 1. 검수관 총평 및 결론**: 전원 일치(PASS) 여부 및 외주사 전달용 종합 의견이 맨 위에 표시됨
2. **📊 2. 주차 종합 대조 요약표**: 동영상별 재생시간, 대응 SB 슬라이드 번호 및 장수, 일치 판정 결과
3. **🔍 3. 동영상별 정밀 검증 내역 및 컨택트시트**: 15~25초 간격으로 타일링된 **시계열 풀프레임 컨택트시트**가 포함되어 슬라이드 노출 근거를 3초 만에 시각적으로 확인 가능

---

## 🔒 7. 절대 안전 보안 수칙 (Strict Read-Only)

본 시스템의 수집 모듈은 시스템의 데이터를 일체 '수정', '삭제', '등록'하지 않습니다.  
오직 HTTP GET/조회 API를 통한 **안전한 단방향 조회 및 다운로드**만 수행하므로 안심하고 사용하실 수 있습니다.
