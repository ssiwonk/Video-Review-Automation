import os
import gc
import sys
import cv2
import numpy as np
from scenedetect import SceneManager, open_video, ContentDetector
from scenedetect.scene_manager import save_images

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class VideoAnalyzer:
    def __init__(self, video_path: str):
        self.video_path = video_path
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

    def make_contact_sheet(self, out_path: str, interval: int = 20):
        """
        영상에서 interval초 간격으로 프레임을 추출하고,
        우측 하단의 LCDMS 페이지 카운터 영역만 잘라내어 컨택트시트로 생성
        """
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if fps <= 0:
            fps = 30.0
        duration = total_frames / fps

        crops, labels = [], []
        for t in range(5, int(duration), interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ret, frame = cap.read()
            if not ret:
                continue
            h, w = frame.shape[:2]
            # 우측 하단 페이지 카운터 영역 (화면 비율 기준: y 50%~56.5%, x 89.5%~97.5%)
            crop = frame[int(h * 0.50):int(h * 0.565), int(w * 0.895):int(w * 0.975)]
            if crop.size > 0:
                crops.append(cv2.resize(crop, (240, 90)))
                mm, ss = divmod(t, 60)
                labels.append(f"{mm:02d}:{ss:02d}")

        cap.release()

        if not crops:
            print("[-] 추출된 프레임이 없습니다.")
            return False

        cols = 6
        rows = (len(crops) + cols - 1) // cols
        cell_w, cell_h = 240, 115
        sheet = np.ones((rows * cell_h, cols * cell_w, 3), dtype=np.uint8) * 255
        for i, (crop, label) in enumerate(zip(crops, labels)):
            r, c = divmod(i, cols)
            y0, x0 = r * cell_h, c * cell_w
            sheet[y0:y0 + 90, x0:x0 + 240] = crop
            cv2.putText(sheet, label, (x0 + 5, y0 + 108), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        cv2.imwrite(out_path, sheet)
        print(f"[+] 컨택트시트 저장 완료: {out_path} ({len(crops)}개 프레임)")
        return True

    def detect_scenes(self, out_dir: str, threshold: float = 27.0):
        """
        PySceneDetect를 이용하여 화면 전환(슬라이드 변경) 시점 감지 및 대표 프레임 저장
        """
        os.makedirs(out_dir, exist_ok=True)
        video = open_video(self.video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))
        scene_manager.detect_scenes(video)

        scene_list = scene_manager.get_scene_list()
        print(f"[+] 화면 전환 감지: 총 {len(scene_list)}개 슬라이드 구간 발견")

        save_images(
            scene_list=scene_list,
            video=video,
            num_images=1,
            output_dir=out_dir,
            image_name_template="Slide_$SCENE_NUMBER_$TIMECODE"
        )

        try:
            if hasattr(video, 'close'):
                video.close()
        except Exception:
            pass
        del video
        gc.collect()

        return scene_list

    def sample_frames(self, seconds_list: list[int], out_dir: str):
        """
        의심 구간의 특정 초(second) 시점의 원본 전체 프레임 추출
        """
        os.makedirs(out_dir, exist_ok=True)
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        saved = []
        for s in seconds_list:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(s * fps))
            ret, frame = cap.read()
            if ret:
                mm, ss = divmod(s, 60)
                out_name = f"Frame_{mm:02d}m_{ss:02d}s.jpg"
                path = os.path.join(out_dir, out_name)
                cv2.imwrite(path, frame)
                saved.append(path)

        cap.release()
        return saved
