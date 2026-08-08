Mini uyku dedektörü.

Yüzünü takip eder. İki durumda tetiklenir:

1. **Yüz ekrandan çıkınca** (öne eğilme / kameradan kaybolma)
2. **Gözler birkaç saniye kapalı kalınca**

Tetiklenince senin seçtiğin **görsel + müzik** açılır: ekranın solunda görsel, sağında canlı kamera. Gözünü açınca veya yüzün geri gelince her şey kapanır, tekrar izlemeye döner.

---

## Nasıl çalışıyor?

- **MediaPipe Face Landmarker** yüz ve göz noktalarını bulur.
- Göz açıklığı **EAR (Eye Aspect Ratio)** ile ölçülür. Değer eşiğin altına düşünce göz “kapalı” sayılır.
- Yüz bir süre algılanmazsa “yüz gitti” sayılır.
- Müzik `ffplay` (ffmpeg) ile, istediğin saniyeden başlatılarak çalınır (macOS / Windows).

```text
[ izleme ] --yüz yok / göz kapalı--> [ sol: görsel | sağ: kamera + müzik ]
     ^                                         |
     +------------- uyanınca ------------------+
```

---

## Gereksinimler

- **macOS** veya **Windows**
- Python 3.10+
- Webcam
- **ffmpeg** (`ffplay` PATH’te olmalı)

### ffmpeg kurulumu

**macOS**

```bash
brew install ffmpeg
```

**Windows** (PowerShell)

```powershell
winget install ffmpeg
```

Kurulumdan sonra yeni bir terminal aç; `ffplay -version` çalışıyorsa tamam.

### Kamera izni

- **macOS:** Sistem Ayarları → Gizlilik ve Güvenlik → Kamera → Terminal / Cursor
- **Windows:** Ayarlar → Gizlilik ve güvenlik → Kamera → erişim açık olsun

---

## Kurulum

**macOS / Linux**

```bash
git clone https://github.com/eisenheiim/sleep-wake.git
cd sleep-wake

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows** (PowerShell / cmd)

```powershell
git clone https://github.com/eisenheiim/sleep-wake.git
cd sleep-wake

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Model

Yüz modeli `models/face_landmarker.task` olarak repoda var. Eksikse:

```bash
# macOS / Linux
mkdir -p models
curl -L -o models/face_landmarker.task \
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
```

```powershell
# Windows
mkdir models -Force
curl -L -o models/face_landmarker.task `
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
# macOS
source .venv/bin/activate
python main.py
```

```powershell
# Windows
.\.venv\Scripts\activate
python main.py
```

- `q` veya `Esc` → çıkış
- Uyanınca görsel/müzik otomatik kapanır

İlk çalıştırmada kamera izni isteyebilir; izin verdikten sonra terminali yeniden başlat.

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
