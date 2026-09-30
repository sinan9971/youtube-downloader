import os
import sys
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp


def setup_ffmpeg_path():
    """Osigurava da je ffmpeg dostupan u PATH varijabli okruženja."""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                user_path = winreg.QueryValueEx(key, "Path")[0]
                for p in user_path.split(";"):
                    if p and p not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]
        except Exception:
            pass

        if not shutil.which("ffmpeg"):
            winget_base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
            if os.path.exists(winget_base):
                for root_dir, dirs, files in os.walk(winget_base):
                    if "ffmpeg.exe" in files:
                        os.environ["PATH"] = root_dir + os.pathsep + os.environ["PATH"]
                        break


def get_default_download_dir():
    """Vraća mapu 'Downloads' korisnika ili mapu aplikacije."""
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.exists(downloads):
        return downloads
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """Dohvaća apsolutni put do resursa, radi za običnu skriptu i za PyInstaller (--onefile)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Downloader")
        self.geometry("640x520")
        self.minsize(580, 480)
        self.configure(bg="#18181b")

        # Postavljanje ikone ako postoji
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.is_downloading = False
        self.save_dir = tk.StringVar(value=get_default_download_dir())
        self.status_var = tk.StringVar(value="Spremno za preuzimanje")
        self.percent_var = tk.StringVar(value="")

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Prilagodba stilova za moderni tamni izgled
        style.configure(".", background="#18181b", foreground="#f4f4f5", font=("Segoe UI", 10))
        
        # Combobox stil
        style.configure(
            "TCombobox",
            fieldbackground="#27272a",
            background="#3f3f46",
            foreground="#ffffff",
            darkcolor="#27272a",
            lightcolor="#27272a",
            arrowcolor="#ffffff",
            padding=5
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#27272a")],
            selectbackground=[("readonly", "#3b82f6")],
            selectforeground=[("readonly", "#ffffff")]
        )

        # Progressbar stil
        style.configure(
            "Red.Horizontal.TProgressbar",
            troughcolor="#27272a",
            background="#ef4444",
            bordercolor="#27272a",
            lightcolor="#ef4444",
            darkcolor="#ef4444"
        )

    def build_ui(self):
        # Glavni okvir
        container = tk.Frame(self, bg="#18181b", padx=25, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Naslov
        title_label = tk.Label(
            container,
            text="YouTube Downloader",
            font=("Segoe UI", 18, "bold"),
            bg="#18181b",
            fg="#ffffff"
        )
        title_label.pack(anchor="w", pady=(0, 2))

        subtitle_label = tk.Label(
            container,
            text="Preuzmite videozapise u MP4 ili zvuk u MP3 visokoj kvaliteti",
            font=("Segoe UI", 9),
            bg="#18181b",
            fg="#a1a1aa"
        )
        subtitle_label.pack(anchor="w", pady=(0, 20))

        # Kartica sa sadržajem
        card = tk.Frame(container, bg="#27272a", padx=20, pady=18, relief=tk.FLAT)
        card.pack(fill=tk.BOTH, expand=True)

        # 1. Polje za YouTube link
        link_label = tk.Label(
            card,
            text="YouTube poveznica (URL):",
            font=("Segoe UI", 10, "bold"),
            bg="#27272a",
            fg="#f4f4f5"
        )
        link_label.pack(anchor="w", pady=(0, 5))

        link_frame = tk.Frame(card, bg="#27272a")
        link_frame.pack(fill=tk.X, pady=(0, 15))

        self.url_entry = tk.Entry(
            link_frame,
            font=("Segoe UI", 11),
            bg="#18181b",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#3f3f46",
            highlightcolor="#ef4444"
        )
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))

        paste_btn = tk.Button(
            link_frame,
            text="Zalijepi",
            font=("Segoe UI", 9, "bold"),
            bg="#3f3f46",
            fg="#ffffff",
            activebackground="#52525b",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=4,
            command=self.paste_from_clipboard
        )
        paste_btn.pack(side=tk.RIGHT)

        # 2. Padajući izbornik za format
        format_label = tk.Label(
            card,
            text="Format i kvaliteta:",
            font=("Segoe UI", 10, "bold"),
            bg="#27272a",
            fg="#f4f4f5"
        )
        format_label.pack(anchor="w", pady=(0, 5))

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
            card,
            values=self.formats,
            state="readonly",
            style="TCombobox",
            font=("Segoe UI", 10)
        )
        self.format_combobox.current(0)
        self.format_combobox.pack(fill=tk.X, pady=(0, 15), ipady=2)

        # 3. Odabir mape za spremanje
        folder_label = tk.Label(
            card,
            text="Spremi u mapu:",
            font=("Segoe UI", 10, "bold"),
            bg="#27272a",
            fg="#f4f4f5"
        )
        folder_label.pack(anchor="w", pady=(0, 5))

        folder_frame = tk.Frame(card, bg="#27272a")
        folder_frame.pack(fill=tk.X, pady=(0, 20))

        self.folder_entry = tk.Entry(
            folder_frame,
            textvariable=self.save_dir,
            font=("Segoe UI", 10),
            bg="#18181b",
            fg="#a1a1aa",
            relief=tk.FLAT,
            state="readonly",
            highlightthickness=1,
            highlightbackground="#3f3f46"
        )
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        browse_btn = tk.Button(
            folder_frame,
            text="Promijeni...",
            font=("Segoe UI", 9),
            bg="#3f3f46",
            fg="#ffffff",
            activebackground="#52525b",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=4,
            command=self.choose_directory
        )
        browse_btn.pack(side=tk.RIGHT)

        # 4. Veliki gumb 'Preuzmi'
        self.download_btn = tk.Button(
            card,
            text="PREUZMI",
            font=("Segoe UI", 12, "bold"),
            bg="#dc2626",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            cursor="hand2",
            pady=10,
            command=self.start_download
        )
        self.download_btn.pack(fill=tk.X, pady=(0, 15))

        # 5. Traka napretka i status
        self.progress_bar = ttk.Progressbar(
            card,
            style="Red.Horizontal.TProgressbar",
            mode="determinate",
            value=0
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        status_frame = tk.Frame(card, bg="#27272a")
        status_frame.pack(fill=tk.X)

        self.status_lbl = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="#a1a1aa",
            anchor="w"
        )
        self.status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.open_folder_btn = tk.Button(
            status_frame,
            text="Otvori mapu",
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="#38bdf8",
            activebackground="#27272a",
            activeforeground="#0284c7",
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
            command=self.open_download_folder
        )
        self.open_folder_btn.pack(side=tk.RIGHT)

    def paste_from_clipboard(self):
        try:
            text = self.clipboard_get().strip()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, text)
        except Exception:
            pass

    def choose_directory(self):
        selected = filedialog.askdirectory(initialdir=self.save_dir.get(), title="Odaberite mapu za spremanje")
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

            if speed:
                if speed > 1024 * 1024:
                    speed_str = f"{speed / (1024 * 1024):.2f} MB/s"
                else:
                    speed_str = f"{speed / 1024:.1f} KB/s"
            else:
                speed_str = "--"

            if eta is not None:
                mins, secs = divmod(int(eta), 60)
                eta_str = f"{mins:02d}:{secs:02d}"
            else:
                eta_str = "--:--"

            msg = f"Preuzimanje: {percent:.1f}% ({speed_str}, preostalo: {eta_str})"
            self.after(0, self.update_ui_progress, percent, msg)

        elif d["status"] == "finished":
            self.after(0, self.update_ui_progress, 100, "Obrada datoteke / spajanje zvuka i videa...")

    def run_download_thread(self, url, format_choice, save_dir):
        try:
            self.after(0, self.update_ui_progress, 0, "Dohvaćam podatke o videu...")

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

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.after(0, self.download_completed, True, "Preuzimanje uspješno završeno!")

        except Exception as e:
            err_msg = str(e)
            if "ffmpeg" in err_msg.lower():
                err_msg += "\n\nNapomena: FFmpeg je obavezan za obradu. Provjerite je li FFmpeg instaliran."
            self.after(0, self.download_completed, False, f"Greška: {err_msg}")

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

        # Pokreni preuzimanje u pozadinskoj dretvi kako se GUI ne bi blokirao
        thread = threading.Thread(
            target=self.run_download_thread,
            args=(url, format_choice, save_dir),
            daemon=True
        )
        thread.start()


def main():
    setup_ffmpeg_path()
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
