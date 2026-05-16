import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from pathlib import Path
import time
import math

from utils import (
    load_settings, 
    save_settings, 
    load_history, 
    add_to_history, 
    open_folder, 
    open_file, 
    fetch_thumbnail
)
from downloader import SnagTubeDownloader

class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("SnagTube - Pro Video Downloader")
        self.geometry("900x700")
        self.minsize(800, 600)
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Load Settings
        self.settings = load_settings()
        self.history = load_history()
        
        self.downloader = SnagTubeDownloader(
            on_progress=self.handle_progress,
            on_success=self.handle_success,
            on_error=self.handle_error,
            on_info_fetched=self.handle_info_fetched
        )
        
        self.current_video_info = None
        self.last_download_path = None
        
        self.setup_ui()

    def setup_ui(self):
        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SnagTube", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.nav_home_btn = ctk.CTkButton(self.sidebar_frame, text="Home", command=self.show_home)
        self.nav_home_btn.grid(row=1, column=0, padx=20, pady=10)
        
        self.nav_history_btn = ctk.CTkButton(self.sidebar_frame, text="History", command=self.show_history)
        self.nav_history_btn.grid(row=2, column=0, padx=20, pady=10)
        
        self.nav_settings_btn = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.show_settings)
        self.nav_settings_btn.grid(row=3, column=0, padx=20, pady=10)
        
        self.notice_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Notice: Only download\nvideos you own or\nhave permission to.\nRespect ToS & Copyright.",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            justify="center"
        )
        self.notice_label.grid(row=5, column=0, padx=20, pady=20, sticky="s")
        
        # Main Content Area
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Initialize views
        self.init_home_view()
        self.init_history_view()
        self.init_settings_view()
        
        # Start at Home
        self.show_home()

    def hide_all_views(self):
        self.home_frame.grid_remove()
        self.history_frame.grid_remove()
        self.settings_frame.grid_remove()

    def show_home(self):
        self.hide_all_views()
        self.home_frame.grid(row=0, column=0, sticky="nsew")

    def show_history(self):
        self.hide_all_views()
        self.refresh_history()
        self.history_frame.grid(row=0, column=0, sticky="nsew")

    def show_settings(self):
        self.hide_all_views()
        self.settings_frame.grid(row=0, column=0, sticky="nsew")

    # --- Home View ---
    def init_home_view(self):
        self.home_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.home_frame.grid_columnconfigure(0, weight=1)
        self.home_frame.grid_rowconfigure(3, weight=1)
        
        # Top: URL Input
        self.url_frame = ctk.CTkFrame(self.home_frame)
        self.url_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.url_frame.grid_columnconfigure(0, weight=1)
        
        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="Paste link here (YouTube, etc.)...")
        self.url_entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")
        
        self.paste_btn = ctk.CTkButton(self.url_frame, text="Paste", width=60, command=self.paste_url)
        self.paste_btn.grid(row=0, column=1, padx=5, pady=10)
        
        self.fetch_btn = ctk.CTkButton(self.url_frame, text="Fetch Info", width=80, command=self.start_fetch)
        self.fetch_btn.grid(row=0, column=2, padx=(5, 10), pady=10)
        
        # Middle: Video Info (Hidden until fetched)
        self.info_frame = ctk.CTkFrame(self.home_frame)
        self.info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        self.info_frame.grid_columnconfigure(1, weight=1)
        
        self.thumbnail_label = ctk.CTkLabel(self.info_frame, text="No Video Selected", width=160, height=90, fg_color="gray20", corner_radius=8)
        self.thumbnail_label.grid(row=0, column=0, rowspan=3, padx=10, pady=10)
        
        self.title_label = ctk.CTkLabel(self.info_frame, text="Title: -", font=ctk.CTkFont(weight="bold"), anchor="w", justify="left")
        self.title_label.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 0))
        
        self.channel_label = ctk.CTkLabel(self.info_frame, text="Channel: -", anchor="w")
        self.channel_label.grid(row=1, column=1, sticky="ew", padx=10)
        
        self.duration_label = ctk.CTkLabel(self.info_frame, text="Duration: -", anchor="w")
        self.duration_label.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 10))
        
        # Download Options
        self.options_frame = ctk.CTkFrame(self.home_frame)
        self.options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        self.options_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.options_frame, text="Format:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.format_var = ctk.StringVar(value=self.settings.get("default_format", "video"))
        self.format_menu = ctk.CTkOptionMenu(self.options_frame, values=["video", "audio"], variable=self.format_var, command=self.on_format_change)
        self.format_menu.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(self.options_frame, text="Quality:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.quality_var = ctk.StringVar(value=self.settings.get("default_quality", "best"))
        self.quality_menu = ctk.CTkOptionMenu(self.options_frame, values=["best", "1080p", "720p", "360p"], variable=self.quality_var)
        self.quality_menu.grid(row=0, column=3, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(self.options_frame, text="Save to:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.folder_var = ctk.StringVar(value=self.settings.get("download_folder", ""))
        self.folder_entry = ctk.CTkEntry(self.options_frame, textvariable=self.folder_var, state="readonly")
        self.folder_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        
        self.browse_btn = ctk.CTkButton(self.options_frame, text="Browse", width=60, command=self.browse_folder)
        self.browse_btn.grid(row=1, column=3, padx=10, pady=10, sticky="w")
        
        self.single_video_var = ctk.BooleanVar(value=True)
        self.single_video_checkbox = ctk.CTkCheckBox(self.options_frame, text="Single Video Only (Ignore Playlist)", variable=self.single_video_var)
        self.single_video_checkbox.grid(row=2, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="w")
        
        # Progress & Actions
        self.action_frame = ctk.CTkFrame(self.home_frame)
        self.action_frame.grid(row=3, column=0, sticky="sew")
        self.action_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(self.action_frame, text="Ready", text_color="gray")
        self.status_label.grid(row=0, column=0, columnspan=2, pady=(10, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self.action_frame)
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)
        
        self.stats_label = ctk.CTkLabel(self.action_frame, text="0% | 0 MB/s | ETA: 0s", font=ctk.CTkFont(size=11))
        self.stats_label.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        self.btn_frame = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        self.download_btn = ctk.CTkButton(self.btn_frame, text="Download", command=self.start_download, fg_color="green", hover_color="darkgreen")
        self.download_btn.pack(side="left", padx=10)
        
        self.cancel_btn = ctk.CTkButton(self.btn_frame, text="Cancel", command=self.cancel_download, state="disabled", fg_color="red", hover_color="darkred")
        self.cancel_btn.pack(side="left", padx=10)
        
        self.open_file_btn = ctk.CTkButton(self.btn_frame, text="Open File", command=self.open_downloaded_file, state="disabled")
        self.open_folder_btn = ctk.CTkButton(self.btn_frame, text="Open Folder", command=self.open_downloaded_folder, state="disabled")

    # --- History View ---
    def init_history_view(self):
        self.history_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.history_frame.grid_columnconfigure(0, weight=1)
        self.history_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.history_frame, text="Download History", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        self.history_scroll = ctk.CTkScrollableFrame(self.history_frame)
        self.history_scroll.grid(row=1, column=0, sticky="nsew")

    def refresh_history(self):
        # Clear existing
        for widget in self.history_scroll.winfo_children():
            widget.destroy()
            
        self.history = load_history()
        
        if not self.history:
            ctk.CTkLabel(self.history_scroll, text="No download history yet.").pack(pady=20)
            return
            
        for item in self.history:
            frame = ctk.CTkFrame(self.history_scroll)
            frame.pack(fill="x", pady=5, padx=5)
            frame.grid_columnconfigure(0, weight=1)
            
            title = ctk.CTkLabel(frame, text=item.get("title", "Unknown"), font=ctk.CTkFont(weight="bold"), anchor="w")
            title.grid(row=0, column=0, sticky="w", padx=10, pady=(5, 0))
            
            detail = ctk.CTkLabel(frame, text=f"{item.get('channel', '')} | {item.get('timestamp', '')[:10]}", font=ctk.CTkFont(size=10), text_color="gray", anchor="w")
            detail.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 5))
            
            btn = ctk.CTkButton(frame, text="Open", width=60, command=lambda p=item.get('filepath'): open_file(p))
            btn.grid(row=0, column=1, rowspan=2, padx=10, pady=5)

    # --- Settings View ---
    def init_settings_view(self):
        self.settings_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.settings_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.settings_frame, text="Settings", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Default folder
        group = ctk.CTkFrame(self.settings_frame)
        group.grid(row=1, column=0, sticky="ew")
        group.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(group, text="Default Download Folder:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.settings_folder_var = ctk.StringVar(value=self.settings.get("download_folder", ""))
        ctk.CTkEntry(group, textvariable=self.settings_folder_var, state="readonly").grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(group, text="Change", width=60, command=self.change_default_folder).grid(row=0, column=2, padx=10, pady=10)

    # --- Actions ---
    def paste_url(self):
        try:
            clipboard = self.clipboard_get()
            self.url_entry.delete(0, 'end')
            self.url_entry.insert(0, clipboard)
        except Exception:
            pass

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def change_default_folder(self):
        folder = filedialog.askdirectory(initialdir=self.settings_folder_var.get())
        if folder:
            self.settings_folder_var.set(folder)
            self.settings["download_folder"] = folder
            save_settings(self.settings)
            self.folder_var.set(folder) # Update home view as well

    def on_format_change(self, choice):
        if choice == "audio":
            self.quality_menu.configure(state="disabled")
        else:
            self.quality_menu.configure(state="normal")

    def format_time(self, seconds):
        if not seconds:
            return "Unknown"
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def start_fetch(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL.")
            return
            
        self.fetch_btn.configure(state="disabled")
        self.status_label.configure(text="Fetching video info...", text_color="blue")
        self.current_video_info = None
        
        # Reset UI
        self.thumbnail_label.configure(image=None, text="Loading...")
        self.title_label.configure(text="Title: -")
        self.channel_label.configure(text="Channel: -")
        self.duration_label.configure(text="Duration: -")
        self.open_file_btn.pack_forget()
        self.open_folder_btn.pack_forget()
        
        single_video = self.single_video_var.get() if hasattr(self, 'single_video_var') else True
        self.downloader.fetch_info(url, single_video=single_video)

    def handle_info_fetched(self, info):
        self.current_video_info = info
        
        # Extract available qualities
        formats = info.get('formats', [])
        available_heights = set()
        for f in formats:
            h = f.get('height')
            if h and h > 0:
                available_heights.add(h)
        
        sorted_heights = sorted(list(available_heights), reverse=True)
        quality_options = [f"{h}p" for h in sorted_heights]
        
        # Add 'best' option
        if not quality_options:
            quality_options = ["best"]
        else:
            if "best" not in quality_options:
                quality_options.insert(0, "best")

        # Truncate title if too long
        title = info.get('title', 'Unknown Title')
        if len(title) > 60:
            title = title[:57] + "..."
            
        # Update UI in main thread
        def update_ui():
            self.title_label.configure(text=f"Title: {title}")
            self.channel_label.configure(text=f"Channel: {info.get('uploader', 'Unknown')}")
            self.duration_label.configure(text=f"Duration: {self.format_time(info.get('duration'))}")
            self.status_label.configure(text="Info fetched successfully. Ready to download.", text_color="green")
            self.fetch_btn.configure(state="normal")
            
            # Update quality menu values
            self.quality_menu.configure(values=quality_options)
            
            # Set default if possible
            default_q = self.settings.get("default_quality", "best")
            if default_q in quality_options:
                self.quality_var.set(default_q)
            else:
                self.quality_var.set("best")

            # Fetch thumbnail
            thumb_url = info.get('thumbnail')
            if thumb_url:
                threading.Thread(target=self._load_thumbnail, args=(thumb_url,), daemon=True).start()
            else:
                self.thumbnail_label.configure(text="No Thumbnail")

        self.after(0, update_ui)

    def _load_thumbnail(self, url):
        img = fetch_thumbnail(url)
        if img:
            # Resize
            img.thumbnail((160, 90))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 90))
            self.after(0, lambda: self.thumbnail_label.configure(image=ctk_img, text=""))
        else:
            self.after(0, lambda: self.thumbnail_label.configure(text="Failed to load thumbnail"))

    def start_download(self):
        url = self.url_entry.get().strip()
        folder = self.folder_var.get()
        fmt = self.format_var.get()
        quality = self.quality_var.get()
        single_video = self.single_video_var.get() if hasattr(self, 'single_video_var') else True
        
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL first.")
            return
            
        if not Path(folder).exists():
            messagebox.showerror("Error", "Selected folder does not exist.")
            return
            
        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.fetch_btn.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        
        self.progress_bar.set(0)
        self.stats_label.configure(text="Starting download...")
        self.status_label.configure(text="Downloading...", text_color="blue")
        
        self.open_file_btn.pack_forget()
        self.open_folder_btn.pack_forget()
        
        self.downloader.download(url, folder, fmt, quality, single_video=single_video)

    def cancel_download(self):
        self.downloader.cancel()
        self.status_label.configure(text="Cancelling...", text_color="orange")
        self.cancel_btn.configure(state="disabled")

    def handle_progress(self, d):
        if d['status'] == 'downloading':
            # Calculate metrics
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            
            if total > 0:
                percent = downloaded / total
                percent_str = f"{percent * 100:.1f}%"
            else:
                percent = 0
                percent_str = "N/A"
                
            speed_mb = speed / 1024 / 1024 if speed else 0
            
            def update_ui():
                self.progress_bar.set(percent)
                self.stats_label.configure(text=f"{percent_str} | {speed_mb:.2f} MB/s | ETA: {self.format_time(eta)}")
                
            self.after(0, update_ui)
            
        elif d['status'] == 'finished':
            self.after(0, lambda: self.status_label.configure(text="Processing file (merging/converting)...", text_color="blue"))

    def handle_success(self, filepath, info):
        self.last_download_path = filepath
        
        # Add to history
        video_info = self.current_video_info if self.current_video_info else info
        add_to_history(video_info, filepath)
        
        def update_ui():
            self.status_label.configure(text="Download complete!", text_color="green")
            self.progress_bar.set(1.0)
            self.stats_label.configure(text="100% | Done")
            self.reset_download_buttons()
            
            # Show action buttons
            self.open_file_btn.configure(state="normal")
            self.open_folder_btn.configure(state="normal")
            self.open_file_btn.pack(side="left", padx=10)
            self.open_folder_btn.pack(side="left", padx=10)
            
        self.after(0, update_ui)

    def handle_error(self, message):
        def update_ui():
            self.status_label.configure(text=message, text_color="red")
            self.reset_download_buttons()
            if "cancelled" not in message.lower():
                messagebox.showerror("Download Error", message)
                
        self.after(0, update_ui)

    def reset_download_buttons(self):
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.fetch_btn.configure(state="normal")
        self.url_entry.configure(state="normal")

    def open_downloaded_file(self):
        if self.last_download_path:
            open_file(self.last_download_path)

    def open_downloaded_folder(self):
        if self.last_download_path:
            open_folder(self.last_download_path)

if __name__ == "__main__":
    app = AppUI()
    app.mainloop()
