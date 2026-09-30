# YouTube Downloader (Desktop & Android) 🎬🎵

Moderna i jednostavna aplikacija za preuzimanje YouTube videozapisa u **MP4** formatu i zvuka u **MP3** formatu, dostupna za **Windows** (GUI i Setup instalacija) i **Android** (Kivy / APK).

---

## 🚀 Značajke

- **Izbor formata i kvalitete:**
  - MP4 video (Najbolja kvaliteta, 1080p Full HD, 720p HD, 480p, 360p)
  - MP3 audio (320 kbps, 192 kbps, 128 kbps)
- **Moderan GUI (Tkinter & Kivy):**
  - Tamna tema (Dark mode)
  - Gumb za brzo lijepljenje linka iz međuspremnika (Clipboard)
  - Precizna traka napretka (postotak, brzina prijenosa u MB/s, preostalo vrijeme)
- **Rad u pozadini (Multithreading):** Sučelje ostaje fluidno i ne zamrzava se tijekom preuzimanja.
- **Windows instalacijski paket:** Inno Setup konfiguracija (`YouTube_Downloader_Setup.exe`) s prečacima na radnoj površini i mogućnošću deinstalacije.
- **Android podrška:** Kivy sučelje i Buildozer konfiguracija za izradu `.apk` paketa.

---

## 🖥️ Windows (Desktop verzija)

### Pokretanje iz izvornog koda:
```bash
# 1. Klonirajte repozitorij
git clone https://github.com/sinan9971/youtube-downloader.git
cd youtube-downloader

# 2. Instalirajte ovisnosti
pip install yt-dlp pillow

# 3. Pokrenite aplikaciju
python youtube_downloader.py
```

> **Napomena:** Za pretvorbu u MP3 i spajanje visokih rezolucija preporučuje se instaliran **FFmpeg** (`winget install Gyan.FFmpeg`).

### Izrada samostalne `.exe` datoteke:
```bash
pip install pyinstaller
python -m PyInstaller --onefile --noconsole --clean --icon=icon.ico --add-data "icon.ico;." youtube_downloader.py
```

### Izrada Windows Setup instalera (Inno Setup):
Otvorite `installer.iss` u programu Inno Setup Compiler i kliknite **Compile** (ili pokrenite `iscc installer.iss`).

---

## 📱 Android verzija (Kivy & Buildozer)

Glavna datoteka za Android je `main.py`.

### Izrada APK-a preko GitHub Actions (u oblaku):
Repozitorij već sadrži `.github/workflows/build_apk.yml`. Prilikom svakog pusha na `main` granu, GitHub Actions automatski gradi APK koji možete preuzeti pod karticom **Actions -> Artifacts**.

### Izrada APK-a lokalno (Linux / WSL2):
```bash
pip install buildozer cython
buildozer android debug
```
Gotov APK nalazit će se u mapi `bin/`.

---

## 📄 Licenca
Ovaj projekt je namijenjen za edukativne svrhe. Poštujte autorska prava i uvjete korištenja platforme YouTube.
