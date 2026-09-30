import os
import sys
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.utils import platform
from kivy.graphics import Color, Rectangle, RoundedRectangle
import yt_dlp


def request_android_permissions():
    """Zatraži dozvole na Androidu (pohrana i internet)."""
    if platform == "android":
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
        except Exception as e:
            print(f"[Android] Greška pri traženju dozvola: {e}")


def get_download_path():
    """Određuje mapu za spremanje ovisno o platformi."""
    if platform == "android":
        try:
            from android.storage import primary_external_storage_path
            storage = primary_external_storage_path()
            dl_dir = os.path.join(storage, "Download")
            if os.path.exists(dl_dir):
                return dl_dir
        except Exception:
            pass

        if os.path.exists("/sdcard/Download"):
            return "/sdcard/Download"
        return os.path.expanduser("~")
    else:
        dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(dl_dir):
            return dl_dir
        return os.path.dirname(os.path.abspath(__file__))


class YouTubeDownloaderApp(App):
    def build(self):
        self.title = "YouTube Downloader"
        self.is_downloading = False
        self.save_dir = get_download_path()

        # Zatraži dozvole pri pokretanju na Androidu
        request_android_permissions()

        # Glavni kontejner
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        # Pozadina aplikacije (tamna tema)
        with root.canvas.before:
            Color(0.09, 0.09, 0.11, 1)  # #18181b
            self.bg_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # 1. Naslov i podnaslov
        title_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(60))
        title_label = Label(
            text="YouTube Downloader",
            font_size=sp(22),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(34),
            halign="center"
        )
        subtitle_label = Label(
            text="MP4 Video & MP3 Audio za Android",
            font_size=sp(12),
            color=(0.63, 0.63, 0.67, 1),
            size_hint_y=None,
            height=dp(20),
            halign="center"
        )
        title_box.add_widget(title_label)
        title_box.add_widget(subtitle_label)
        root.add_widget(title_box)

        # 2. Polje za unos linka i gumb za lijepljenje
        url_section = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(80), spacing=dp(6))
        url_label = Label(
            text="YouTube poveznica (URL):",
            font_size=sp(13),
            bold=True,
            color=(0.95, 0.95, 0.96, 1),
            size_hint_y=None,
            height=dp(22),
            halign="left"
        )
        url_label.bind(size=self._align_label_left)
        url_section.add_widget(url_label)

        input_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
        self.url_input = TextInput(
            hint_text="Zalijepite YouTube link ovdje...",
            multiline=False,
            font_size=sp(14),
            background_color=(0.15, 0.15, 0.18, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.94, 0.27, 0.27, 1),
            padding=[dp(10), dp(12), dp(10), dp(12)]
        )
        paste_btn = Button(
            text="Zalijepi",
            font_size=sp(13),
            bold=True,
            size_hint_x=None,
            width=dp(90),
            background_color=(0.25, 0.25, 0.28, 1),
            color=(1, 1, 1, 1)
        )
        paste_btn.bind(on_release=self.paste_clipboard)
        input_row.add_widget(self.url_input)
        input_row.add_widget(paste_btn)
        url_section.add_widget(input_row)
        root.add_widget(url_section)

        # 3. Odabir formata (Spinner)
        format_section = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(74), spacing=dp(6))
        format_label = Label(
            text="Format i kvaliteta:",
            font_size=sp(13),
            bold=True,
            color=(0.95, 0.95, 0.96, 1),
            size_hint_y=None,
            height=dp(22),
            halign="left"
        )
        format_label.bind(size=self._align_label_left)
        format_section.add_widget(format_label)

        self.format_spinner = Spinner(
            text="MP4 Video (Najbolja kvaliteta)",
            values=(
                "MP4 Video (Najbolja kvaliteta)",
                "MP4 Video (720p HD)",
                "MP4 Video (480p / 360p)",
                "MP3 / Audio (Najbolja kvaliteta)",
                "MP3 / Audio (128 kbps - Brzo)"
            ),
            font_size=sp(13),
            size_hint_y=None,
            height=dp(44),
            background_color=(0.18, 0.18, 0.22, 1),
            color=(1, 1, 1, 1)
        )
        format_section.add_widget(self.format_spinner)
        root.add_widget(format_section)

        # 4. Prikaz mape za spremanje
        save_info = Label(
            text=f"Sprema se u: {self.save_dir}",
            font_size=sp(11),
            color=(0.55, 0.55, 0.60, 1),
            size_hint_y=None,
            height=dp(24),
            halign="left"
        )
        save_info.bind(size=self._align_label_left)
        root.add_widget(save_info)

        # 5. Veliki gumb 'Preuzmi'
        self.download_btn = Button(
            text="PREUZMI",
            font_size=sp(16),
            bold=True,
            size_hint_y=None,
            height=dp(54),
            background_color=(0.86, 0.15, 0.15, 1),  # Crvena boja
            color=(1, 1, 1, 1)
        )
        self.download_btn.bind(on_release=self.start_download)
        root.add_widget(self.download_btn)

        # 6. Traka napretka (ProgressBar)
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(16)
        )
        root.add_widget(self.progress_bar)

        # 7. Status label
        self.status_label = Label(
            text="Spremno za preuzimanje",
            font_size=sp(12),
            color=(0.7, 0.7, 0.75, 1),
            size_hint_y=None,
            height=dp(40),
            halign="center",
            valign="middle"
        )
        self.status_label.bind(size=self._align_label_center)
        root.add_widget(self.status_label)

        # Fleksibilni prazan prostor pri dnu
        root.add_widget(BoxLayout())

        return root

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _align_label_left(self, instance, value):
        instance.text_size = (instance.width, None)

    def _align_label_center(self, instance, value):
        instance.text_size = (instance.width, instance.height)

    def paste_clipboard(self, instance):
        text = Clipboard.paste()
        if text:
            self.url_input.text = text.strip()

    def update_ui_progress(self, percent, message):
        self.progress_bar.value = percent
        self.status_label.text = message

    def download_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed", 0)

            percent = (downloaded / total * 100) if total > 0 else 0

            if speed:
                if speed > 1024 * 1024:
                    speed_str = f"{speed / (1024 * 1024):.2f} MB/s"
                else:
                    speed_str = f"{speed / 1024:.1f} KB/s"
            else:
                speed_str = "--"

            msg = f"Preuzimanje: {percent:.1f}% ({speed_str})"
            Clock.schedule_once(lambda dt: self.update_ui_progress(percent, msg))

        elif d["status"] == "finished":
            Clock.schedule_once(lambda dt: self.update_ui_progress(100, "Obrada datoteke..."))

    def run_download_thread(self, url, format_choice, save_dir):
        try:
            Clock.schedule_once(lambda dt: self.update_ui_progress(0, "Dohvaćam video podatke..."))

            is_mp3 = "Audio" in format_choice or "MP3" in format_choice
            outtmpl = os.path.join(save_dir, "%(title)s.%(ext)s")

            if is_mp3:
                # Za mobilne uređaje koristimo audio format koji ne zahtijeva nužno eksterni ffmpeg ako nije dostupan
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "progress_hooks": [self.download_hook],
                    "quiet": True,
                    "no_warnings": True,
                }
            else:
                if "720p" in format_choice:
                    fmt = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best"
                elif "480p" in format_choice or "360p" in format_choice:
                    fmt = "best[height<=480][ext=mp4]/best[height<=360][ext=mp4]/best"
                else:
                    fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

                ydl_opts = {
                    "format": fmt,
                    "outtmpl": outtmpl,
                    "progress_hooks": [self.download_hook],
                    "quiet": True,
                    "no_warnings": True,
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            Clock.schedule_once(lambda dt: self.on_download_complete(True, "Preuzimanje uspješno završeno!"))

        except Exception as e:
            err = str(e)
            Clock.schedule_once(lambda dt: self.on_download_complete(False, f"Greška: {err[:60]}..."))

    def on_download_complete(self, success, message):
        self.is_downloading = False
        self.download_btn.disabled = False
        self.download_btn.text = "PREUZMI"
        self.download_btn.background_color = (0.86, 0.15, 0.15, 1)

        if success:
            self.progress_bar.value = 100
            self.status_label.text = "✓ " + message
            self.status_label.color = (0.2, 0.8, 0.3, 1)
        else:
            self.progress_bar.value = 0
            self.status_label.text = "✗ " + message
            self.status_label.color = (0.9, 0.3, 0.3, 1)

    def start_download(self, instance):
        if self.is_downloading:
            return

        url = self.url_input.text.strip()
        if not url:
            self.status_label.text = "Molimo unesite YouTube link!"
            self.status_label.color = (0.9, 0.7, 0.2, 1)
            return

        self.is_downloading = True
        self.download_btn.disabled = True
        self.download_btn.text = "PREUZIMANJE U TIJEKU..."
        self.download_btn.background_color = (0.5, 0.1, 0.1, 1)
        self.progress_bar.value = 0
        self.status_label.text = "Pokretanje..."
        self.status_label.color = (0.7, 0.7, 0.75, 1)

        format_choice = self.format_spinner.text

        thread = threading.Thread(
            target=self.run_download_thread,
            args=(url, format_choice, self.save_dir),
            daemon=True
        )
        thread.start()


if __name__ == "__main__":
    YouTubeDownloaderApp().run()
