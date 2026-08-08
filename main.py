"""
sleep-wake — kamera ile uyku tespiti.

İki tetik:
1) Yüz ekrandan çıkınca (önde eğilme / kamera dışı)
2) Gözler 2 saniye kapalı kalınca

Tetiklenince ekran ikiye bölünür: solda görsel, sağda kamera (+ müzik).
Göz açılınca veya yüz geri gelince görsel/müzik kapanır.
Çıkış: q
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options as base_options_module

# --- Ayarlar ---
EYES_CLOSED_SECONDS = 2.0
FACE_GONE_SECONDS = 0.8  # kısa debounce; titreme olmasın
AWAKE_CONFIRM_SECONDS = 0.4  # uyanınca hemen titreme olmasın
EAR_THRESHOLD = 0.21  # göz kapalı eşiği (gerekirse ayarla)
# 1) yüz ekrandan çıkınca → wake.* @ 15s
# 2) gözler 2 sn kapalı → wake2.* @ 41s
AUDIO_FACE_GONE_START = 15
AUDIO_EYES_CLOSED_START = 41
SLEEP_VIEW_SCALE = 0.82  # uyku görünümü ekranın bu oranı (tam ekran değil)
CAMERA_INDEX = 0
WINDOW_NAME = "sleep-wake"

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
MODEL_PATH = ROOT / "models" / "face_landmarker.task"
IMAGE_FACE_GONE_CANDIDATES = ("wake.jpg", "wake.jpeg", "wake.png", "wake.webp")
IMAGE_EYES_CLOSED_CANDIDATES = ("wake2.png", "wake2.jpg", "wake2.jpeg", "wake2.webp")
AUDIO_FACE_GONE_CANDIDATES = ("wake.mp3", "wake.wav", "wake.m4a", "wake.ogg")
AUDIO_EYES_CLOSED_CANDIDATES = ("wake2.mp3", "wake2.wav", "wake2.m4a", "wake2.ogg")

# Face Landmarker — sol/sağ göz EAR noktaları
LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)


def find_asset(names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = ASSETS / name
        if path.is_file():
            return path
    return None


def eye_aspect_ratio(landmarks, indices, w: int, h: int) -> float:
    pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
    v1 = np.linalg.norm(np.array(pts[1]) - np.array(pts[5]))
    v2 = np.linalg.norm(np.array(pts[2]) - np.array(pts[4]))
    hdist = np.linalg.norm(np.array(pts[0]) - np.array(pts[3]))
    if hdist < 1e-6:
        return 0.0
    return float((v1 + v2) / (2.0 * hdist))


def load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Görsel okunamadı: {path}")
    return img


def screen_size() -> tuple[int, int]:
    """macOS masaüstü boyutu; başarısızsa varsayılan."""
    try:
        out = subprocess.check_output(
            [
                "osascript",
                "-e",
                'tell application "Finder" to get bounds of window of desktop',
            ],
            text=True,
        ).strip()
        parts = [int(p.strip()) for p in out.split(",")]
        return max(800, parts[2] - parts[0]), max(600, parts[3] - parts[1])
    except Exception:
        return 1440, 900


def fit_cover(img: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Paneli dolduracak şekilde kırpıp ölçekle."""
    tw, th = size
    h, w = img.shape[:2]
    scale = max(tw / max(w, 1), th / max(h, 1))
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    x0 = max(0, (nw - tw) // 2)
    y0 = max(0, (nh - th) // 2)
    crop = resized[y0 : y0 + th, x0 : x0 + tw]
    if crop.shape[0] != th or crop.shape[1] != tw:
        crop = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_AREA)
    return crop


def compose_split(
    wake_img: np.ndarray, camera_frame: np.ndarray, screen_w: int, screen_h: int
) -> np.ndarray:
    """Sol yarı görsel, sağ yarı kamera — tam ekran bölünmüş görünüm."""
    left_w = screen_w // 2
    right_w = screen_w - left_w
    left = fit_cover(wake_img, (left_w, screen_h))
    right = fit_cover(camera_frame, (right_w, screen_h))
    return np.hstack([left, right])


class MusicPlayer:
    """ffplay ile müzik — istenen saniyeden başlar, döngüde çalar."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None

    def play(self, path: Path, start_seconds: float = 0) -> None:
        self.stop()
        cmd = [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "quiet",
            "-loop",
            "0",
            "-ss",
            str(max(0.0, float(start_seconds))),
            str(path),
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None


def create_landmarker() -> vision.FaceLandmarker:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Model yok: {MODEL_PATH}\n"
            "models/face_landmarker.task dosyasını indir."
        )
    options = vision.FaceLandmarkerOptions(
        base_options=base_options_module.BaseOptions(
            model_asset_path=str(MODEL_PATH)
        ),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.FaceLandmarker.create_from_options(options)


def main() -> None:
    image_face_gone = find_asset(IMAGE_FACE_GONE_CANDIDATES)
    image_eyes_closed = find_asset(IMAGE_EYES_CLOSED_CANDIDATES)
    audio_face_gone = find_asset(AUDIO_FACE_GONE_CANDIDATES)
    audio_eyes_closed = find_asset(AUDIO_EYES_CLOSED_CANDIDATES)

    if image_face_gone is None:
        print(
            "assets/ klasörüne wake.jpg / wake.png koy (yüz kaybolunca).\n"
            f"Beklenen klasör: {ASSETS}"
        )
        return
    if image_eyes_closed is None:
        print(
            "assets/ klasörüne wake2.png / wake2.jpeg koy (gözler kapanınca).\n"
            f"Beklenen klasör: {ASSETS}"
        )
        return
    if audio_face_gone is None:
        print(
            "assets/ klasörüne wake.mp3 koy (yüz kaybolunca).\n"
            f"Beklenen klasör: {ASSETS}"
        )
        return
    if audio_eyes_closed is None:
        print(
            "assets/ klasörüne wake2.mp3 koy (gözler kapanınca).\n"
            f"Beklenen klasör: {ASSETS}"
        )
        return

    img_face_gone = load_image(image_face_gone)
    img_eyes_closed = load_image(image_eyes_closed)
    active_wake_img = img_face_gone
    music = MusicPlayer()
    landmarker = create_landmarker()

    # macOS'ta AVFoundation backend izin diyaloğunu daha güvenilir tetikler
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(
            "Kamera açılamadı — büyük ihtimalle macOS kamera izni yok.\n\n"
            "Sistem Ayarları → Gizlilik ve Güvenlik → Kamera\n"
            "  → Cursor (ve/veya Terminal) için izni AÇ\n\n"
            "Sonra Cursor'ı tamamen kapatıp yeniden aç, tekrar dene:\n"
            "  python main.py"
        )
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera",
            ],
            check=False,
        )
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    eyes_closed_since: float | None = None
    face_gone_since: float | None = None
    awake_since: float | None = None
    sleeping = False
    trigger_reason = ""
    frame_ts_ms = 0

    sw, sh = screen_size()
    sleep_w = max(960, int(sw * SLEEP_VIEW_SCALE))
    sleep_h = max(540, int(sh * SLEEP_VIEW_SCALE))
    sleep_x = max(0, (sw - sleep_w) // 2)
    sleep_y = max(0, (sh - sleep_h) // 2)

    print("Çalışıyor. q = çıkış")
    print("Uyku → sol görsel | sağ kamera (ortalı pencere)")
    print(
        f"Yüz kaybolunca: {image_face_gone.name} + "
        f"{audio_face_gone.name} @{AUDIO_FACE_GONE_START}s"
    )
    print(
        f"Gözler kapanınca: {image_eyes_closed.name} + "
        f"{audio_eyes_closed.name} @{AUDIO_EYES_CLOSED_START}s"
    )
    print(f"Uyku penceresi: {sleep_w}x{sleep_h}")

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    was_sleeping = False

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Kameradan kare alınamadı.")
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            frame_ts_ms += 33
            result = landmarker.detect_for_video(mp_image, frame_ts_ms)

            now = time.monotonic()
            status = "yuz yok"
            face_present = False
            eyes_closed = False
            ear = 0.0

            if result.face_landmarks:
                face_present = True
                face_gone_since = None
                lm = result.face_landmarks[0]
                left_ear = eye_aspect_ratio(lm, LEFT_EYE, w, h)
                right_ear = eye_aspect_ratio(lm, RIGHT_EYE, w, h)
                ear = (left_ear + right_ear) / 2.0
                eyes_closed = ear < EAR_THRESHOLD

                for idx in LEFT_EYE + RIGHT_EYE:
                    x = int(lm[idx].x * w)
                    y = int(lm[idx].y * h)
                    cv2.circle(frame, (x, y), 1, (180, 180, 180), -1)

                if eyes_closed:
                    if eyes_closed_since is None:
                        eyes_closed_since = now
                    closed_for = now - eyes_closed_since
                    remain = max(0.0, EYES_CLOSED_SECONDS - closed_for)
                    status = f"goz kapali {closed_for:.1f}s"
                    if not sleeping and remain > 0:
                        cv2.putText(
                            frame,
                            f"uyku: {remain:.1f}s",
                            (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.0,
                            (40, 40, 220),
                            2,
                            cv2.LINE_AA,
                        )
                    if not sleeping and closed_for >= EYES_CLOSED_SECONDS:
                        trigger_reason = "gözler 2 sn kapalı"
                        sleeping = True
                        active_wake_img = img_eyes_closed
                        music.play(audio_eyes_closed, AUDIO_EYES_CLOSED_START)
                        print(
                            f"Tetik: {trigger_reason} → "
                            f"{image_eyes_closed.name} + "
                            f"{audio_eyes_closed.name} @{AUDIO_EYES_CLOSED_START}s"
                        )
                else:
                    eyes_closed_since = None
                    status = f"uyanik  EAR={ear:.2f}"
            else:
                eyes_closed_since = None
                if face_gone_since is None:
                    face_gone_since = now
                gone_for = now - face_gone_since
                status = f"yuz yok {gone_for:.1f}s"
                if not sleeping and gone_for >= FACE_GONE_SECONDS:
                    trigger_reason = "yüz ekrandan çıktı"
                    sleeping = True
                    active_wake_img = img_face_gone
                    music.play(audio_face_gone, AUDIO_FACE_GONE_START)
                    print(
                        f"Tetik: {trigger_reason} → "
                        f"{image_face_gone.name} + "
                        f"{audio_face_gone.name} @{AUDIO_FACE_GONE_START}s"
                    )

            # Uyanma: yüz geri geldi VEYA gözler açıldı
            is_awake = face_present and not eyes_closed
            if sleeping:
                if is_awake:
                    if awake_since is None:
                        awake_since = now
                    if now - awake_since >= AWAKE_CONFIRM_SECONDS:
                        music.stop()
                        sleeping = False
                        eyes_closed_since = None
                        face_gone_since = None
                        awake_since = None
                        print("Uyanıldı — görsel/müzik kapandı.")
                else:
                    awake_since = None
            else:
                awake_since = None

            cv2.putText(
                frame,
                status,
                (20, h - 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (220, 220, 220),
                2,
                cv2.LINE_AA,
            )

            if sleeping:
                if not was_sleeping:
                    cv2.resizeWindow(WINDOW_NAME, sleep_w, sleep_h)
                    cv2.moveWindow(WINDOW_NAME, sleep_x, sleep_y)
                    was_sleeping = True
                view = compose_split(active_wake_img, frame, sleep_w, sleep_h)
            else:
                if was_sleeping:
                    was_sleeping = False
                view = frame

            cv2.imshow(WINDOW_NAME, view)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
    finally:
        music.stop()
        landmarker.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
