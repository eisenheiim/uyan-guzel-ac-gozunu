# sleep-wake

Kamera ile “uyudun mu?” diyen küçük bir masaüstü uygulaması.

Yüzünü takip eder. İki durumda tetiklenir:

1. **Yüz ekrandan çıkınca** (öne eğilme / kameradan kaybolma)
2. **Gözler birkaç saniye kapalı kalınca**

Tetiklenince senin seçtiğin **görsel + müzik** açılır: ekranın solunda görsel, sağında canlı kamera. Gözünü açınca veya yüzün geri gelince her şey kapanır, tekrar izlemeye döner.

Instagram / Reels için ekran kaydı almak çok kolay: uygulama sade bir OpenCV penceresi.

---

## Nasıl çalışıyor?

- **MediaPipe Face Landmarker** yüz ve göz noktalarını bulur.
- Göz açıklığı **EAR (Eye Aspect Ratio)** ile ölçülür. Değer eşiğin altına düşünce göz “kapalı” sayılır.
- Yüz bir süre algılanmazsa “yüz gitti” sayılır.
- Müzik macOS’ta `ffplay` ile, istediğin saniyeden başlatılarak çalınır.

```text
[ izleme ] --yüz yok / göz kapalı--> [ sol: görsel | sağ: kamera + müzik ]
     ^                                         |
     +------------- uyanınca ------------------+
```

---

## Gereksinimler

- macOS (müzik için `ffplay` / Homebrew `ffmpeg`)
- Python 3.10+
- Webcam
- Kamera izni (Sistem Ayarları → Gizlilik ve Güvenlik → Kamera → Terminal veya Cursor)

```bash
brew install ffmpeg
```

---

## Kurulum

```bash
git clone https://github.com/eisenheiim/sleep-wake.git
cd sleep-wake

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Model

Yüz modeli `models/face_landmarker.task` olarak repoda var. Eksikse:

```bash
mkdir -p models
curl -L -o models/face_landmarker.task \
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
```

### Görsel ve müzik (`assets/`)

Repoda hazır örnek medya var. İstersen kendi dosyalarınla değiştir:

| Dosya | Ne zaman? | Müzik başlangıcı |
|--------|-----------|------------------|
| `wake.png` + `wake.mp3` | Yüz ekrandan çıkınca | **15. saniye** |
| `wake2.jpeg` + `wake2.mp3` | Gözler kapalı kalınca | **41. saniye** |

Desteklenen uzantılar: görsel `.png` / `.jpg` / `.jpeg` / `.webp` · ses `.mp3` / `.wav` / `.m4a` / `.ogg`

---

## Çalıştır

```bash
source .venv/bin/activate
python main.py
```

- `q` veya `Esc` → çıkış
- Uyanınca görsel/müzik otomatik kapanır

İlk çalıştırmada macOS kamera izni isteyebilir. İzin verdikten sonra uygulamayı (Terminal/Cursor) yeniden başlat.

---

## Ayarlar (`main.py` üstü)

| Sabit | Anlamı | Varsayılan |
|--------|--------|------------|
| `EYES_CLOSED_SECONDS` | Gözler kaç sn kapalı kalınca tetik | `2.0` |
| `FACE_GONE_SECONDS` | Yüz kaç sn yoksa tetik | `0.8` |
| `EAR_THRESHOLD` | Göz kapalı eşiği (hassasiyet) | `0.21` |
| `AUDIO_FACE_GONE_START` | 1. müziğin başlangıç saniyesi | `15` |
| `AUDIO_EYES_CLOSED_START` | 2. müziğin başlangıç saniyesi | `41` |
| `SLEEP_VIEW_SCALE` | Uyku penceresinin ekran oranı | `0.82` |
| `AWAKE_CONFIRM_SECONDS` | Uyanma debounce (titreme önleme) | `0.4` |

Göz algısı yanlış tetikleniyorsa `EAR_THRESHOLD` değerini biraz yükselt; algılamıyorsa düşür.

---

## Proje yapısı

```text
sleep-wake/
├── main.py              # uygulama
├── requirements.txt
├── README.md
├── assets/
│   ├── wake.png / wake.mp3      # yüz kaybolunca
│   └── wake2.jpeg / wake2.mp3   # gözler kapanınca
└── models/
    └── face_landmarker.task
```

---

## Bağımlılıklar

- `opencv-python` — kamera ve pencere
- `mediapipe` — yüz / göz landmark
- `numpy`
- `ffmpeg` / `ffplay` — müzik (sistem paketi)

---

## Lisans

MIT — kullan, fork’la, kendi versiyonunu çek.
