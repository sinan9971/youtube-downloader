import os
import sys
import shutil
import zipfile
import urllib.request
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp

# ─────────────────────────────────────────────────────────────
# FFmpeg auto-preuzimanje i detekcija
# ─────────────────────────────────────────────────────────────

# Statička Win64 FFmpeg binarna datoteka (GPL, bez instalacije)
FFMPEG_DOWNLOAD_URL = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)

def get_app_dir():
    """Vraća direktorij aplikacije (radi i za .exe i za .py)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_local_ffmpeg_dir():
    """Vraća lokalnu mapu ffmpeg/ unutar direktorija aplikacije."""
    return os.path.join(get_app_dir(), "ffmpeg")


def find_ffmpeg():
    """
    Traži ffmpeg.exe u redoslijedu:
      1. Lokalna mapa ffmpeg/ (uz aplikaciju)
      2. Korisnički PATH (registar Windows)
      3. WinGet instalirani paketi
      4. Sistemski PATH (shutil.which)
    Vraća puni put do ffmpeg.exe ili None.
    """
    # 1. Lokalna mapa uz aplikaciju
    local_ffmpeg = os.path.join(get_local_ffmpeg_dir(), "ffmpeg.exe")
    if os.path.isfile(local_ffmpeg):
        return local_ffmpeg

    # 2. Korisnički PATH iz Windows registra
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                user_path = winreg.QueryValueEx(key, "Path")[0]
                for p in user_path.split(";"):
                    candidate = os.path.join(p.strip(), "ffmpeg.exe")
                    if os.path.isfile(candidate):
                        return candidate
        except Exception:
            pass

        # 3. WinGet paketi
        winget_base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
        if os.path.exists(winget_base):
            for root_dir, _dirs, files in os.walk(winget_base):
                if "ffmpeg.exe" in files:
                    return os.path.join(root_dir, "ffmpeg.exe")

    # 4. Sistemski PATH
    found = shutil.which("ffmpeg")
    return found


def setup_ffmpeg_path(ffmpeg_path=None):
    """
    Postavi ffmpeg putanju u os.environ["PATH"] da je yt-dlp može pronaći.
    Ako je ffmpeg_path None, pokušaj automatski pronaći.
    """
    if ffmpeg_path is None:
        ffmpeg_path = find_ffmpeg()

    if ffmpeg_path and os.path.isfile(ffmpeg_path):
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        if ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        return ffmpeg_path
    return None


def download_ffmpeg(progress_callback=None):
    """
    Preuzima statički FFmpeg ZIP s GitHuba i raspakira ffmpeg.exe u lokalnu
    mapu ffmpeg/ uz aplikaciju. Vraća putanju do ffmpeg.exe pri uspjehu.
    progress_callback(percent, message) — opcionalna.
    """
    local_dir = get_local_ffmpeg_dir()
    os.makedirs(local_dir, exist_ok=True)
    zip_path = os.path.join(local_dir, "ffmpeg_temp.zip")

    def reporthook(count, block_size, total_size):
        if total_size > 0 and progress_callback:
            percent = min(count * block_size * 100 // total_size, 99)
            downloaded_mb = count * block_size / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            progress_callback(percent, f"Preuzimanje FFmpeg: {percent}% ({downloaded_mb:.1f} / {total_mb:.1f} MB)")

    try:
        if progress_callback:
            progress_callback(0, "Spajanje na GitHub za preuzimanje FFmpeg...")
        urllib.request.urlretrieve(FFMPEG_DOWNLOAD_URL, zip_path, reporthook)

        if progress_callback:
            progress_callback(99, "Raspakiranje FFmpeg arhive...")

        ffmpeg_exe = None
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                # Traži bin/ffmpeg.exe unutar ZIP-a
                if member.endswith("bin/ffmpeg.exe") or member.endswith("bin\\ffmpeg.exe"):
                    # Raspakiraj samo ffmpeg.exe u lokalni direktorij
                    source = zf.open(member)
                    ffmpeg_exe = os.path.join(local_dir, "ffmpeg.exe")
                    with open(ffmpeg_exe, "wb") as target:
                        target.write(source.read())
                    break

        os.remove(zip_path)

        if ffmpeg_exe and os.path.isfile(ffmpeg_exe):
            if progress_callback:
                progress_callback(100, "FFmpeg uspješno instaliran!")
            return ffmpeg_exe

    except Exception as e:
        # Počisti neuspjelu datoteku
        if os.path.exists(zip_path):
            os.remove(zip_path)
        raise RuntimeError(f"Preuzimanje FFmpeg-a nije uspjelo:\n{e}")

    return None


# ─────────────────────────────────────────────────────────────
# Pomoćne funkcije aplikacije
# ─────────────────────────────────────────────────────────────

def get_default_download_dir():
    """Vraća mapu 'Downloads' korisnika ili mapu aplikacije."""
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.exists(downloads):
        return downloads
    return get_app_dir()


def get_resource_path(relative_path):
    """Dohvaća apsolutni put do resursa (PyInstaller kompatibilno)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ─────────────────────────────────────────────────────────────
# GUI aplikacija
# ─────────────────────────────────────────────────────────────

class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Downloader")
        self.geometry("640x560")
        self.minsize(580, 520)
        self.configure(bg="#18181b")

        # Ikonica
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.is_downloading = False
        self.ffmpeg_path = None  # Bit će postavljen nakon provjere/preuzimanja
        self.save_dir = tk.StringVar(value=get_default_download_dir())
        self.status_var = tk.StringVar(value="Provjera FFmpeg-a...")
        self.ffmpeg_status_var = tk.StringVar(value="⏳  Provjera FFmpeg-a...")

        self.setup_styles()
        self.build_ui()

        # Provjeri FFmpeg u pozadini odmah po pokretanju
        threading.Thread(target=self._init_ffmpeg, daemon=True).start()

    # ── Stilovi ──────────────────────────────────────────────

    def setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background="#18181b", foreground="#f4f4f5", font=("Segoe UI", 10))
        style.configure(
            "TCombobox",
            fieldbackground="#27272a", background="#3f3f46",
            foreground="#ffffff", darkcolor="#27272a", lightcolor="#27272a",
            arrowcolor="#ffffff", padding=5
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#27272a")],
            selectbackground=[("readonly", "#3b82f6")],
            selectforeground=[("readonly", "#ffffff")]
        )
        style.configure(
            "Red.Horizontal.TProgressbar",
            troughcolor="#27272a", background="#ef4444",
            bordercolor="#27272a", lightcolor="#ef4444", darkcolor="#ef4444"
        )
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#27272a", background="#22c55e",
            bordercolor="#27272a", lightcolor="#22c55e", darkcolor="#22c55e"
        )

    # ── Izgradnja GUI-ja ──────────────────────────────────────

    def build_ui(self):
        container = tk.Frame(self, bg="#18181b", padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Naslov
        tk.Label(
            container, text="YouTube Downloader",
            font=("Segoe UI", 18, "bold"), bg="#18181b", fg="#ffffff"
        ).pack(anchor="w", pady=(0, 2))
        tk.Label(
            container, text="Preuzmite videozapise u MP4 ili zvuk u MP3 visokoj kvaliteti",
            font=("Segoe UI", 9), bg="#18181b", fg="#a1a1aa"
        ).pack(anchor="w", pady=(0, 12))

        # ── FFmpeg statusna traka ─────────────────────────────
        ffmpeg_frame = tk.Frame(container, bg="#1c1c1f", padx=12, pady=8, relief=tk.FLAT)
        ffmpeg_frame.pack(fill=tk.X, pady=(0, 12))

        self.ffmpeg_status_lbl = tk.Label(
            ffmpeg_frame, textvariable=self.ffmpeg_status_var,
            font=("Segoe UI", 9), bg="#1c1c1f", fg="#a1a1aa", anchor="w"
        )
        self.ffmpeg_status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.ffmpeg_dl_btn = tk.Button(
            ffmpeg_frame, text="Preuzmi FFmpeg",
            font=("Segoe UI", 9, "bold"),
            bg="#dc2626", fg="#ffffff",
            activebackground="#b91c1c", activeforeground="#ffffff",
            relief=tk.FLAT, cursor="hand2", padx=10, pady=2,
            command=self._download_ffmpeg_manually
        )
        # Gumb je skriven dok ne utvrdimo da FFmpeg nedostaje
        self.ffmpeg_dl_btn.pack(side=tk.RIGHT)
        self.ffmpeg_dl_btn.pack_forget()

        # ── Kartica ──────────────────────────────────────────
        card = tk.Frame(container, bg="#27272a", padx=20, pady=18, relief=tk.FLAT)
        card.pack(fill=tk.BOTH, expand=True)

        # 1. Link
        tk.Label(
            card, text="YouTube poveznica (URL):",
            font=("Segoe UI", 10, "bold"), bg="#27272a", fg="#f4f4f5"
        ).pack(anchor="w", pady=(0, 5))

        link_frame = tk.Frame(card, bg="#27272a")
        link_frame.pack(fill=tk.X, pady=(0, 15))

        self.url_entry = tk.Entry(
            link_frame, font=("Segoe UI", 11),
            bg="#18181b", fg="#ffffff", insertbackground="#ffffff",
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground="#3f3f46", highlightcolor="#ef4444"
        )
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))

        tk.Button(
            link_frame, text="Zalijepi",
            font=("Segoe UI", 9, "bold"),
            bg="#3f3f46", fg="#ffffff",
            activebackground="#52525b", activeforeground="#ffffff",
            relief=tk.FLAT, cursor="hand2", padx=12, pady=4,
            command=self.paste_from_clipboard
        ).pack(side=tk.RIGHT)

        # 2. Format
        tk.Label(
            card, text="Format i kvaliteta:",
            font=("Segoe UI", 10, "bold"), bg="#27272a", fg="#f4f4f5"
        ).pack(anchor="w", pady=(0, 5))

        self.formats = [
            "MP4 Video (Najbolja kvaliteta)",
            "MP4 Video (1080p Full HD)",
            "MP4 Video (720p HD)",
            "MP4 Video (480p)",
            "MP3 Audio (320 kbps - Najviša kvaliteta)",
            "MP3 Audio (192 kbps - Standardna kvaliteta)",
            "MP3 Audio (128 kbps - Manja datoteka)"
        ]
        self.format_combobox = ttk.Combobox(
            card, values=self.formats, state="readonly",
            style="TCombobox", font=("Segoe UI", 10)
        )
        self.format_combobox.current(0)
        self.format_combobox.pack(fill=tk.X, pady=(0, 15), ipady=2)

        # 3. Mapa za spremanje
        tk.Label(
            card, text="Spremi u mapu:",
            font=("Segoe UI", 10, "bold"), bg="#27272a", fg="#f4f4f5"
        ).pack(anchor="w", pady=(0, 5))

        folder_frame = tk.Frame(card, bg="#27272a")
        folder_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Entry(
            folder_frame, textvariable=self.save_dir,
            font=("Segoe UI", 10), bg="#18181b", fg="#a1a1aa",
            relief=tk.FLAT, state="readonly",
            highlightthickness=1, highlightbackground="#3f3f46"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        tk.Button(
            folder_frame, text="Promijeni...",
            font=("Segoe UI", 9),
            bg="#3f3f46", fg="#ffffff",
            activebackground="#52525b", activeforeground="#ffffff",
            relief=tk.FLAT, cursor="hand2", padx=10, pady=4,
            command=self.choose_directory
        ).pack(side=tk.RIGHT)

        # 4. Gumb Preuzmi
        self.download_btn = tk.Button(
            card, text="PREUZMI",
            font=("Segoe UI", 12, "bold"),
            bg="#dc2626", fg="#ffffff",
            activebackground="#b91c1c", activeforeground="#ffffff",
            relief=tk.FLAT, cursor="hand2", pady=10,
            command=self.start_download
        )
        self.download_btn.pack(fill=tk.X, pady=(0, 15))

        # 5. Traka napretka + status
        self.progress_bar = ttk.Progressbar(
            card, style="Red.Horizontal.TProgressbar",
            mode="determinate", value=0
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        status_frame = tk.Frame(card, bg="#27272a")
        status_frame.pack(fill=tk.X)

        self.status_lbl = tk.Label(
            status_frame, textvariable=self.status_var,
            font=("Segoe UI", 9), bg="#27272a", fg="#a1a1aa", anchor="w"
        )
        self.status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(
            status_frame, text="Otvori mapu",
            font=("Segoe UI", 9),
            bg="#27272a", fg="#38bdf8",
            activebackground="#27272a", activeforeground="#0284c7",
            relief=tk.FLAT, cursor="hand2", bd=0,
            command=self.open_download_folder
        ).pack(side=tk.RIGHT)

    # ── FFmpeg inicijalizacija ────────────────────────────────

    def _init_ffmpeg(self):
        """Pozadinska dretve: provjeri FFmpeg, preuzmi ako nedostaje."""
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            self.ffmpeg_path = setup_ffmpeg_path(ffmpeg)
            self.after(0, self._on_ffmpeg_found, ffmpeg)
        else:
            self.after(0, self._on_ffmpeg_missing)
            # Automatski pokušaj preuzeti bez pitanja
            try:
                self.after(0, lambda: self.ffmpeg_status_var.set("⬇️  Preuzimanje FFmpeg-a u pozadini..."))
                ffmpeg_path = download_ffmpeg(progress_callback=self._ffmpeg_dl_progress)
                if ffmpeg_path:
                    self.ffmpeg_path = setup_ffmpeg_path(ffmpeg_path)
                    self.after(0, self._on_ffmpeg_found, ffmpeg_path)
            except Exception as e:
                self.after(0, self._on_ffmpeg_download_failed, str(e))

    def _ffmpeg_dl_progress(self, percent, message):
        """Ažurira FFmpeg status traku tijekom preuzimanja (iz pozadinske dretve)."""
        self.after(0, lambda: self.ffmpeg_status_var.set(f"⬇️  {message}"))
        self.after(0, lambda: self.progress_bar.configure(value=percent))

    def _on_ffmpeg_found(self, path):
        """Poziva se kad je FFmpeg pronađen ili uspješno preuzet."""
        short = path if len(path) < 55 else "..." + path[-52:]
        self.ffmpeg_status_var.set(f"✅  FFmpeg: {short}")
        self.ffmpeg_status_lbl.config(fg="#22c55e")
        self.ffmpeg_dl_btn.pack_forget()
        self.progress_bar.configure(value=0)
        self.status_var.set("Spremno za preuzimanje")

    def _on_ffmpeg_missing(self):
        """Poziva se kad FFmpeg nije pronađen — prikaži gumb za ručno preuzimanje."""
        self.ffmpeg_status_var.set("⚠️  FFmpeg nije pronađen — pokušavam automatski preuzeti...")
        self.ffmpeg_status_lbl.config(fg="#f59e0b")
        self.ffmpeg_dl_btn.pack(side=tk.RIGHT)

    def _on_ffmpeg_download_failed(self, error_msg):
        """Poziva se kad automatsko preuzimanje FFmpeg-a nije uspjelo."""
        self.ffmpeg_status_var.set("❌  FFmpeg nije dostupan — MP3 i 1080p neće raditi")
        self.ffmpeg_status_lbl.config(fg="#ef4444")
        self.ffmpeg_dl_btn.config(text="Pokušaj ponovo")
        self.ffmpeg_dl_btn.pack(side=tk.RIGHT)
        self.status_var.set("Upozorenje: FFmpeg nedostaje")

    def _download_ffmpeg_manually(self):
        """Gumb za ručno pokretanje preuzimanja FFmpeg-a."""
        self.ffmpeg_dl_btn.config(state=tk.DISABLED, text="Preuzimanje...")
        self.ffmpeg_status_var.set("⬇️  Preuzimanje FFmpeg-a...")
        self.ffmpeg_status_lbl.config(fg="#38bdf8")
        threading.Thread(target=self._init_ffmpeg, daemon=True).start()

    # ── Radnje korisnika ─────────────────────────────────────

    def paste_from_clipboard(self):
        try:
            text = self.clipboard_get().strip()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, text)
        except Exception:
            pass

    def choose_directory(self):
        selected = filedialog.askdirectory(
            initialdir=self.save_dir.get(), title="Odaberite mapu za spremanje"
        )
        if selected:
            self.save_dir.set(selected)

    def open_download_folder(self):
        folder = self.save_dir.get()
        if os.path.exists(folder):
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])

    # ── Preuzimanje videa ─────────────────────────────────────

    def update_ui_progress(self, percent, message):
        self.progress_bar["value"] = percent
        self.status_var.set(message)

    def download_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed", 0)
            eta = d.get("eta", 0)

            percent = (downloaded / total * 100) if total > 0 else 0

            speed_str = "--"
            if speed:
                speed_str = (
                    f"{speed / (1024 * 1024):.2f} MB/s"
                    if speed > 1024 * 1024
                    else f"{speed / 1024:.1f} KB/s"
                )

            eta_str = "--:--"
            if eta is not None:
                mins, secs = divmod(int(eta), 60)
                eta_str = f"{mins:02d}:{secs:02d}"

            msg = f"Preuzimanje: {percent:.1f}% ({speed_str}, preostalo: {eta_str})"
            self.after(0, self.update_ui_progress, percent, msg)

        elif d["status"] == "finished":
            self.after(0, self.update_ui_progress, 100, "Obrada datoteke / spajanje zvuka i videa...")

    def run_download_thread(self, url, format_choice, save_dir):
        try:
            self.after(0, self.update_ui_progress, 0, "Dohvaćam podatke o videu...")

            # Postavi ffmpeg_location u yt-dlp opcije ako ga imamo
            ffmpeg_location = (
                os.path.dirname(self.ffmpeg_path) if self.ffmpeg_path else None
            )

            is_mp3 = "MP3" in format_choice

            if is_mp3:
                bitrate = "320" if "320" in format_choice else ("128" if "128" in format_choice else "192")
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": os.path.join(save_dir, "%(title)s.%(ext)s"),
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": bitrate,
                        }
                    ],
                    "progress_hooks": [self.download_hook],
                    "quiet": True,
                    "no_warnings": True,
                }
            else:
                if "1080p" in format_choice:
                    fmt = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]"
                elif "720p" in format_choice:
                    fmt = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]"
                elif "480p" in format_choice:
                    fmt = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]"
                else:
                    fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

                ydl_opts = {
                    "format": fmt,
                    "merge_output_format": "mp4",
                    "outtmpl": os.path.join(save_dir, "%(title)s.%(ext)s"),
                    "progress_hooks": [self.download_hook],
                    "quiet": True,
                    "no_warnings": True,
                }

            # Eksplicitno proslijedi ffmpeg lokaciju yt-dlp-u
            if ffmpeg_location:
                ydl_opts["ffmpeg_location"] = ffmpeg_location

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.after(0, self.download_completed, True, "Preuzimanje uspješno završeno!")

        except Exception as e:
            self.after(0, self.download_completed, False, f"Greška: {e}")

    def download_completed(self, success, message):
        self.is_downloading = False
        self.download_btn.config(state=tk.NORMAL, text="PREUZMI", bg="#dc2626")
        self.url_entry.config(state=tk.NORMAL)
        self.format_combobox.config(state="readonly")

        if success:
            self.progress_bar["value"] = 100
            self.status_var.set("✓ " + message)
            messagebox.showinfo("Uspjeh", message)
        else:
            self.progress_bar["value"] = 0
            self.status_var.set("✗ Došlo je do greške.")
            messagebox.showerror("Pogreška pri preuzimanju", message)

    def start_download(self):
        if self.is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Upozorenje", "Molimo unesite YouTube poveznicu (link)!")
            self.url_entry.focus_set()
            return

        save_dir = self.save_dir.get().strip()
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Greška", f"Nije moguće kreirati mapu za spremanje:\n{e}")
                return

        format_choice = self.format_combobox.get()

        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED, text="PREUZIMANJE U TIJEKU...", bg="#7f1d1d")
        self.url_entry.config(state=tk.DISABLED)
        self.format_combobox.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.status_var.set("Pokretanje preuzimanja...")

        thread = threading.Thread(
            target=self.run_download_thread,
            args=(url, format_choice, save_dir),
            daemon=True
        )
        thread.start()


# ─────────────────────────────────────────────────────────────
# Ulazna točka
# ─────────────────────────────────────────────────────────────

def main():
    # Pokušaj pronaći i postaviti FFmpeg u PATH odmah (sinhrono, brzo)
    # Detaljno preuzimanje obavlja se u pozadinskoj dretvi unutar GUI-ja
    quick_find = find_ffmpeg()
    if quick_find:
        setup_ffmpeg_path(quick_find)

    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
