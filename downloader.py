import threading
import traceback
import yt_dlp
from pathlib import Path

class SnagTubeDownloader:
    def __init__(self, 
                 on_progress=None, 
                 on_success=None, 
                 on_error=None,
                 on_info_fetched=None):
        """
        Initializes the downloader with callbacks.
        on_progress: function(d) - Called during download with a dictionary of progress info.
        on_success: function(filepath) - Called when download completes successfully.
        on_error: function(error_message) - Called if an error occurs.
        on_info_fetched: function(info_dict) - Called when video metadata is successfully fetched.
        """
        self.on_progress = on_progress
        self.on_success = on_success
        self.on_error = on_error
        self.on_info_fetched = on_info_fetched
        
        self.is_cancelled = False
        self._current_thread = None

    def cancel(self):
        """Signals the current download to stop."""
        self.is_cancelled = True

    def fetch_info(self, url, single_video=True):
        """Fetches video metadata in a separate thread."""
        if not url:
            if self.on_error:
                self.on_error("Please enter a valid URL.")
            return

        def _fetch():
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'noplaylist': single_video,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if self.on_info_fetched:
                        self.on_info_fetched(info)
            except Exception as e:
                if self.on_error:
                    self.on_error(f"Failed to fetch video info: {str(e)}")

        thread = threading.Thread(target=_fetch, daemon=True)
        thread.start()

    def download(self, url, folder_path, format_type='video', quality='best', single_video=True):
        """
        Starts the download in a separate thread.
        format_type: 'video' (MP4) or 'audio' (MP3)
        quality: '360p', '720p', '1080p', or 'best'
        """
        self.is_cancelled = False
        
        if not Path(folder_path).exists():
            if self.on_error:
                self.on_error("Selected output folder does not exist.")
            return

        def _download():
            ydl_opts = {
                'outtmpl': str(Path(folder_path) / '%(title)s.%(ext)s'),
                'progress_hooks': [self._progress_hook],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': single_video,
            }

            if format_type == 'audio':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                # Video format logic
                if quality == 'best':
                    # Best video + best audio, merged into mp4 if possible
                    ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                    ydl_opts['merge_output_format'] = 'mp4'
                else:
                    # Specific quality (e.g., '1080p' -> '1080')
                    height = quality.replace('p', '')
                    # Prefer MP4 if possible, but fallback to best available for the selected resolution
                    ydl_opts['format'] = f'bestvideo[height={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height={height}]+bestaudio/best[height={height}]'
                    ydl_opts['merge_output_format'] = 'mp4'

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if self.is_cancelled:
                        return # Cancelled, error callback already called in hook

                    filepath = ydl.prepare_filename(info)
                    
                    # If audio, yt-dlp might change the extension to mp3 post-processing
                    if format_type == 'audio':
                        base_path = Path(filepath).with_suffix('.mp3')
                        filepath = str(base_path)

                    if self.on_success:
                        self.on_success(filepath, info)
                        
            except yt_dlp.utils.DownloadError as e:
                if self.is_cancelled:
                    pass # Handled in hook
                elif self.on_error:
                    self.on_error(f"Download Error: {str(e)}")
            except Exception as e:
                if not self.is_cancelled and self.on_error:
                    self.on_error(f"An unexpected error occurred: {str(e)}\n{traceback.format_exc()}")

        self._current_thread = threading.Thread(target=_download, daemon=True)
        self._current_thread.start()

    def _progress_hook(self, d):
        """Hook for yt-dlp progress."""
        if self.is_cancelled:
            if d['status'] == 'downloading':
                # Attempt to stop download by raising an exception
                if self.on_error:
                    self.on_error("Download cancelled by user.")
                raise yt_dlp.utils.DownloadCancelled('Download cancelled by user.')
            return

        if self.on_progress:
            self.on_progress(d)
