


Kamera ile uyuduğunu fark eden küçük bir uygulama.

Uyuyunca (yüzün kaybolunca veya gözlerin kapanınca) senin seçtiğin **görsel + müzik** açılır.  
Uyanınca her şey kapanır.

**Mac** ve **Windows**

---

## Ne yapar?

İki durumda tetiklenir:

1. Yüzün kameradan çıkınca  
2. Gözlerin 2 saniye kapalı kalınca  

Sonra:

- Solda görsel  
- Sağda sen (kamera)  
- Müzik çalar  

Gözünü açınca veya yüzün geri gelince durur.

---

## Başlamadan önce

Bunlar kurulu olsun:

1. [Python](https://www.python.org/downloads/) (3.10 veya üzeri)  
2. Kamera  
3. **ffmpeg** (müzik için gerekli)

### 1) ffmpeg kur

**Mac** (Terminal):

```bash
brew install ffmpeg
```

**Windows** (PowerShell):

```powershell
winget install ffmpeg
```

Kurduktan sonra terminali kapatıp yeniden aç.

Kontrol:

```bash
ffplay -version
```

Bir şey yazıyorsa tamam.

### 2) Kamera izni

- **Mac:** Sistem Ayarları → Gizlilik ve Güvenlik → Kamera → Terminal’e izin ver  
- **Windows:** Ayarlar → Gizlilik → Kamera → açık olsun  

---

## Kurulum (bir kez)

### Mac

```bash
git clone https://github.com/eisenheiim/uyan-guzel-ac-gozunu.git
cd uyan-guzel-ac-gozunu
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows

```powershell
git clone https://github.com/eisenheiim/uyan-guzel-ac-gozunu.git
cd uyan-guzel-ac-gozunu
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Çalıştırma

### Mac

```bash
cd uyan-guzel-ac-gozunu
source .venv/bin/activate
python main.py
```

### Windows

```powershell
cd uyan-guzel-ac-gozunu
.\.venv\Scripts\activate
python main.py
```

Çıkmak için: `q`

---

## Görsel ve müzik

Hazır dosyalar `assets/` klasöründe:

| Durum | Görsel | Müzik | Müzik nereden başlar |
|--------|--------|--------|----------------------|
| Yüz kaybolunca | `wake.png` | `wake.mp3` | 15. saniye |
| Gözler kapanınca | `wake2.jpeg` | `wake2.mp3` | 41. saniye |

Kendi dosyanı koymak istersen aynı isimlerle değiştirmen yeterli.

---

## Ayarlar (istersen)

`main.py` dosyasının en üstünde:

| Ayar | Ne işe yarar | Şu an |
|------|---------------|--------|
| `EYES_CLOSED_SECONDS` | Gözler kaç sn kapalı kalsın | `2` |
| `FACE_GONE_SECONDS` | Yüz kaç sn yok olsun | `0.8` |
| `AUDIO_FACE_GONE_START` | 1. müzik kaçıncı saniyeden | `15` |
| `AUDIO_EYES_CLOSED_START` | 2. müzik kaçıncı saniyeden | `41` |
| `EAR_THRESHOLD` | Göz algısı hassasiyeti | `0.21` |
| `SLEEP_VIEW_SCALE` | Uyku penceresi boyutu | `0.82` |

Gözü yanlış algılıyorsa `EAR_THRESHOLD` değerini biraz büyüt.  
Algılamıyorsa biraz küçült.

---

## Sorun olursa

| Problem | Ne yap |
|---------|--------|
| Kamera açılmıyor | Kamera iznini kontrol et, terminali yeniden aç |
| Müzik çalmıyor | `ffplay -version` dene, ffmpeg kurulu mu bak |
| `python` bulunamadı | Python’u kur, yeni terminal aç |
| Paket hatası | `pip install -r requirements.txt` tekrar çalıştır |

---

## Lisans

MIT — istediğin gibi kullan, paylaş, değiştir.
