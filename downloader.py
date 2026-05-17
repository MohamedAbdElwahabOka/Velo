import threading
import traceback
import yt_dlp
from pathlib import Path
from utils import vtt_to_md

class VeloDownloader:
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
                'extract_flat': 'in_playlist',
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

    def download(self, url, folder_path, format_type='video', quality='best', single_video=True, playlist_items=None, download_transcript=False, clip_start=None, clip_end=None, sponsorblock=False, embed_metadata=False, network_mode='stable', download_archive=False):
        """
        Starts the download in a separate thread.
        format_type: 'video' (MP4) or 'audio' (MP3)
        quality: '360p', '720p', '1080p', or 'best'
        network_mode: 'stable', 'balanced', 'turbo', or 'data_saver'
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
                'continuedl': True,
                'retries': 20,
                'fragment_retries': 20,
                'file_access_retries': 5,
                'extractor_retries': 5,
                'socket_timeout': 30,
            }

            if network_mode == 'turbo':
                ydl_opts.update({
                    'concurrent_fragment_downloads': 6,
                    'http_chunk_size': 10 * 1024 * 1024,
                    'retries': 10,
                    'fragment_retries': 10,
                })
            elif network_mode == 'balanced':
                ydl_opts.update({
                    'concurrent_fragment_downloads': 3,
                    'http_chunk_size': 5 * 1024 * 1024,
                })
            elif network_mode == 'data_saver':
                ydl_opts.update({
                    'concurrent_fragment_downloads': 2,
                    'http_chunk_size': 2 * 1024 * 1024,
                    'retries': 30,
                    'fragment_retries': 30,
                    'socket_timeout': 45,
                })
            if playlist_items:
                ydl_opts['playlist_items'] = playlist_items
            if download_transcript:
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = ['en']
                ydl_opts['subtitlesformat'] = 'vtt'
            if clip_start is not None and clip_end is not None:
                ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(clip_start, clip_end)])

            if download_archive:
                ydl_opts['download_archive'] = str(Path(folder_path) / 'velo_archive.txt')

            if sponsorblock:
                ydl_opts['sponsorblock_remove'] = ['sponsor', 'intro', 'outro', 'interaction']

            if format_type == 'audio':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '96' if network_mode == 'data_saver' else '192',
                }]
            else:
                # Video format logic
                if network_mode == 'data_saver':
                    ydl_opts['format'] = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/worst[ext=mp4]/worst'
                    ydl_opts['merge_output_format'] = 'mp4'
                elif quality == 'best':
                    # Best video + best audio, merged into mp4 if possible
                    ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                    ydl_opts['merge_output_format'] = 'mp4'
                else:
                    # Specific quality (e.g., '1080p' -> '1080')
                    height = quality.replace('p', '')
                    # Prefer MP4 if possible, but fallback to best available for the selected resolution
                    ydl_opts['format'] = f'bestvideo[height={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height={height}]+bestaudio/best[height={height}]'
                    ydl_opts['merge_output_format'] = 'mp4'
            
            if embed_metadata:
                ydl_opts['writethumbnail'] = True
                if 'postprocessors' not in ydl_opts:
                    ydl_opts['postprocessors'] = []
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                })
                ydl_opts['postprocessors'].append({
                    'key': 'EmbedThumbnail',
                    'already_have_thumbnail': False,
                })

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

                    if download_transcript:
                        vtt_path = Path(filepath).with_suffix('.en.vtt')
                        if vtt_path.exists():
                            vtt_to_md(str(vtt_path), info)

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
