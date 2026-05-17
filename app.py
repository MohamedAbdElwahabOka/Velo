import os
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import threading
import queue
import time
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from downloader import VeloDownloader
from clipper import process_clip
from utils import load_settings, save_settings, load_history, add_to_history, clear_history, get_history_stats, open_folder, open_file

APP_VERSION = "1.0.0-pro"

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
CORS(app)

progress_queue = queue.Queue()
downloader = None

# Batch Queue System
batch_queue = queue.Queue()
is_batch_running = False
batch_control = {
    "paused": False,
    "stop_requested": False,
    "total": 0,
    "completed": 0,
    "failed": 0,
    "current_url": "",
    "current_index": 0,
    "last_started_at": None,
    "failed_jobs": [],
    "logs": [],
}
batch_lock = threading.Lock()

def reset_batch_state(total):
    with batch_lock:
        batch_control.update({
            "paused": False,
            "stop_requested": False,
            "total": total,
            "completed": 0,
            "failed": 0,
            "current_url": "",
            "current_index": 0,
            "last_started_at": None,
            "failed_jobs": [],
            "logs": [],
        })

def add_batch_log(status, url, message, filepath=None):
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "url": url,
        "message": message,
        "filepath": filepath or "",
    }
    with batch_lock:
        batch_control["logs"].insert(0, entry)
        batch_control["logs"] = batch_control["logs"][:200]

def get_batch_state():
    with batch_lock:
        state = dict(batch_control)
        state["queued"] = batch_queue.qsize()
        state["running"] = is_batch_running
        return state

def batch_worker():
    global is_batch_running
    while True:
        try:
            job = batch_queue.get(timeout=1.0)
        except queue.Empty:
            break

        if job is None:
            batch_queue.task_done()
            break
            
        url = job['url']
        config = job['config']
        index = job['index']
        total = job['total']

        while get_batch_state()["paused"]:
            progress_queue.put({'type': 'batch_paused'})
            time.sleep(0.8)

        if get_batch_state()["stop_requested"]:
            add_batch_log("skipped", url, "Skipped because queue was stopped")
            batch_queue.task_done()
            continue

        with batch_lock:
            batch_control["current_url"] = url
            batch_control["current_index"] = index
            batch_control["last_started_at"] = datetime.now().isoformat(timespec="seconds")
        
        progress_queue.put({'type': 'batch_status', 'index': index, 'total': total, 'url': url})
        
        # Block until download completes
        event = threading.Event()
        
        def c_prog(d):
            if d['status'] == 'downloading':
                t = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                dl = d.get('downloaded_bytes', 0)
                if t:
                    p = (dl / t) * 100
                    progress_queue.put({'type': 'batch_progress', 'percent': f"{p:.1f}%"})
                    
        def c_succ(filepath, info):
            add_to_history(info, filepath)
            with batch_lock:
                batch_control["completed"] += 1
            add_batch_log("success", url, info.get('title', url), filepath)
            progress_queue.put({'type': 'batch_item_success', 'filepath': filepath, 'title': info.get('title', url)})
            event.set()
            
        def c_err(msg):
            with batch_lock:
                batch_control["failed"] += 1
                batch_control["failed_jobs"].append(job)
            add_batch_log("error", url, msg)
            progress_queue.put({'type': 'batch_item_error', 'message': msg, 'url': url})
            event.set()
            
        def c_info(info):
            pass # Ignore info fetches in batch

        batch_dl = VeloDownloader(on_progress=c_prog, on_success=c_succ, on_error=c_err, on_info_fetched=c_info)
        folder = config.get("folder", str(Path.home() / "Downloads"))
        
        batch_dl.download(
            url, folder, 
            format_type=config.get('format', 'video'), 
            quality=config.get('quality', 'best'), 
            single_video=True, 
            download_transcript=config.get('download_transcript', False),
            sponsorblock=config.get('sponsorblock', False),
            embed_metadata=config.get('embed_metadata', False),
            network_mode=config.get('network_mode', 'stable')
        )
        
        event.wait() # Wait for this download to finish before taking the next
        batch_queue.task_done()

    is_batch_running = False
    with batch_lock:
        batch_control["current_url"] = ""
        batch_control["current_index"] = 0
    progress_queue.put({'type': 'batch_complete'})

def handle_progress(d):
    progress_queue.put({'type': 'progress', 'data': d})

def handle_success(filepath, info):
    add_to_history(info, filepath)
    progress_queue.put({'type': 'success', 'filepath': filepath, 'info': info})

def handle_error(msg):
    progress_queue.put({'type': 'error', 'message': msg})

def handle_info(info):
    progress_queue.put({'type': 'info', 'data': info})

downloader = VeloDownloader(
    on_progress=handle_progress,
    on_success=handle_success,
    on_error=handle_error,
    on_info_fetched=handle_info
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/meta', methods=['GET'])
def api_meta():
    return jsonify({
        "name": "Velo",
        "version": APP_VERSION,
        "status": "ready",
        "features": [
            "low_bandwidth_modes",
            "batch_queue",
            "clip_maker",
            "history_stats",
            "multilingual_ui",
            "reports",
        ],
    })

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'POST':
        settings = request.json
        save_settings(settings)
        return jsonify({"status": "success"})
    settings = load_settings()
    if 'download_folder' not in settings:
        settings['download_folder'] = str(Path.home() / "Downloads")
    return jsonify(settings)

@app.route('/api/select_folder', methods=['POST'])
def api_select_folder():
    def get_folder():
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(title="Select Download Folder")
        root.destroy()
        return folder
        
    folder = get_folder()
    if folder:
        settings = load_settings()
        settings['download_folder'] = folder
        save_settings(settings)
        return jsonify({"folder": folder})
    return jsonify({"error": "No folder selected"}), 400

@app.route('/api/history', methods=['GET', 'DELETE'])
def api_history():
    if request.method == 'DELETE':
        if clear_history():
            return jsonify({"status": "cleared"})
        return jsonify({"error": "Unable to clear history"}), 500
    return jsonify(load_history())

@app.route('/api/stats', methods=['GET'])
def api_stats():
    return jsonify(get_history_stats())

@app.route('/api/report', methods=['GET'])
def api_report():
    fmt = request.args.get("format", "json").lower()
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "app_version": APP_VERSION,
        "stats": get_history_stats(),
        "history": load_history(),
        "batch": get_batch_state(),
    }
    if fmt == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["title", "channel", "url", "filepath", "timestamp"])
        writer.writeheader()
        for item in payload["history"]:
            writer.writerow({
                "title": item.get("title", ""),
                "channel": item.get("channel", ""),
                "url": item.get("url", ""),
                "filepath": item.get("filepath", ""),
                "timestamp": item.get("timestamp", ""),
            })
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=velo-history-report.csv"},
        )
    return jsonify(payload)

@app.route('/api/estimate', methods=['POST'])
def api_estimate():
    data = request.json or {}
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400

    result_queue = queue.Queue()

    def done(info):
        formats = info.get("formats", []) if isinstance(info, dict) else []
        candidates = []
        for item in formats:
            size = item.get("filesize") or item.get("filesize_approx")
            if not size:
                continue
            candidates.append({
                "format_id": item.get("format_id"),
                "ext": item.get("ext"),
                "height": item.get("height"),
                "resolution": item.get("resolution"),
                "filesize": size,
                "format_note": item.get("format_note"),
            })
        candidates = sorted(candidates, key=lambda row: row.get("filesize", 0))
        result_queue.put({
            "title": info.get("title", ""),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail", ""),
            "smallest": candidates[:5],
            "largest": candidates[-5:],
            "known_formats": len(candidates),
        })

    def fail(message):
        result_queue.put({"error": message})

    temp = VeloDownloader(on_info_fetched=done, on_error=fail)
    temp.fetch_info(url, single_video=True)

    try:
        result = result_queue.get(timeout=30)
    except queue.Empty:
        return jsonify({"error": "Unable to estimate size before timeout"}), 504

    status = 400 if "error" in result else 200
    return jsonify(result), status

@app.route('/api/fetch', methods=['POST'])
def api_fetch():
    data = request.json
    url = data.get('url')
    single_video = data.get('single_video', True)
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
        
    threading.Thread(target=downloader.fetch_info, args=(url, single_video), daemon=True).start()
    return jsonify({"status": "fetching"})

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.json
    url = data.get('url')
    
    settings = load_settings()
    folder = settings.get('download_folder', str(Path.home() / "Downloads"))
    
    fmt = data.get('format', 'video')
    quality = data.get('quality', 'best')
    single_video = data.get('single_video', True)
    playlist_items = data.get('playlist_items', None)
    download_transcript = data.get('download_transcript', False)
    sponsorblock = data.get('sponsorblock', False)
    embed_metadata = data.get('embed_metadata', False)
    network_mode = data.get('network_mode', 'stable')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
        
    threading.Thread(target=downloader.download, args=(url, folder, fmt, quality), kwargs={
        'single_video': single_video,
        'playlist_items': playlist_items,
        'download_transcript': download_transcript,
        'sponsorblock': sponsorblock,
        'embed_metadata': embed_metadata,
        'network_mode': network_mode
    }, daemon=True).start()
    return jsonify({"status": "downloading"})

@app.route('/api/batch', methods=['POST'])
def api_batch():
    global is_batch_running
    data = request.json
    urls = data.get('urls', [])
    config = data.get('config', {})
    
    settings = load_settings()
    config['folder'] = settings.get('download_folder', str(Path.home() / "Downloads"))
    
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    reset_batch_state(len(urls))
        
    for i, url in enumerate(urls):
        batch_queue.put({
            'url': url,
            'config': config,
            'index': i + 1,
            'total': len(urls)
        })
        
    if not is_batch_running:
        is_batch_running = True
        threading.Thread(target=batch_worker, daemon=True).start()
        
    return jsonify({"status": "batch queued", "count": len(urls)})

@app.route('/api/batch/state', methods=['GET'])
def api_batch_state():
    return jsonify(get_batch_state())

@app.route('/api/batch/control', methods=['POST'])
def api_batch_control():
    global is_batch_running
    data = request.json or {}
    action = data.get("action")

    with batch_lock:
        if action == "pause":
            batch_control["paused"] = True
        elif action == "resume":
            batch_control["paused"] = False
        elif action == "stop":
            batch_control["stop_requested"] = True
            batch_control["paused"] = False
        elif action == "retry_failed":
            failed_jobs = list(batch_control["failed_jobs"])
            batch_control["failed_jobs"] = []
            batch_control["failed"] = 0
            batch_control["stop_requested"] = False
            batch_control["paused"] = False
        else:
            return jsonify({"error": "Unknown batch action"}), 400

    if action == "retry_failed":
        if not failed_jobs:
            return jsonify({"status": "no failed jobs"})
        total = len(failed_jobs)
        for i, job in enumerate(failed_jobs):
            job["index"] = i + 1
            job["total"] = total
            batch_queue.put(job)
        with batch_lock:
            batch_control["total"] = total
            batch_control["completed"] = 0
            batch_control["current_index"] = 0
            batch_control["current_url"] = ""
        if not is_batch_running:
            is_batch_running = True
            threading.Thread(target=batch_worker, daemon=True).start()

    return jsonify({"status": action, "batch": get_batch_state()})

@app.route('/api/clip', methods=['POST'])
def api_clip():
    data = request.json
    url = data.get('url')
    try:
        start_time = int(data.get('start_time', 0))
        end_time = int(data.get('end_time', 0))
    except ValueError:
        return jsonify({"error": "Start and End times must be numbers"}), 400
        
    top_text = data.get('top_text', '')
    bottom_text = data.get('bottom_text', '')
    format_type = data.get('format_type', 'Short (9:16 MP4)')
    
    if not url or start_time is None or end_time is None:
        return jsonify({"error": "Missing parameters"}), 400
        
    def clip_task():
        progress_queue.put({'type': 'clip_status', 'message': 'Downloading segment...'})
        
        def c_prog(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                dl = d.get('downloaded_bytes', 0)
                if total:
                    percent = (dl / total) * 100
                    progress_queue.put({'type': 'clip_progress', 'percent': f"{percent:.1f}%"})
                
        def c_succ(filepath, info):
            progress_queue.put({'type': 'clip_status', 'message': 'Processing via FFmpeg...'})
            is_short = format_type == "Short (9:16 MP4)"
            is_gif = format_type == "Meme GIF"
            
            output_file = str(Path(filepath).with_name(f"clip_{Path(filepath).name}"))
            
            success, msg_or_path = process_clip(
                filepath, output_file, 
                start_time=None, end_time=None, 
                top_text=top_text, bottom_text=bottom_text, 
                is_short=is_short, is_gif=is_gif
            )
            
            if success:
                progress_queue.put({'type': 'clip_success', 'filepath': msg_or_path})
            else:
                progress_queue.put({'type': 'clip_error', 'message': msg_or_path})
                
        def c_err(msg):
            progress_queue.put({'type': 'clip_error', 'message': msg})
            
        clip_dl = VeloDownloader(on_progress=c_prog, on_success=c_succ, on_error=c_err)
        settings = load_settings()
        folder = settings.get("download_folder", str(Path.home() / "Downloads"))
        
        clip_dl.download(url, folder, format_type='video', quality='best', single_video=True, clip_start=start_time, clip_end=end_time)

    threading.Thread(target=clip_task, daemon=True).start()
    return jsonify({"status": "clipping started"})

@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    downloader.cancel()
    return jsonify({"status": "cancelled"})

@app.route('/api/open', methods=['POST'])
def api_open():
    data = request.json
    path = data.get('path')
    is_folder = data.get('is_folder', False)
    if path:
        if is_folder:
            open_folder(path)
        else:
            open_file(path)
        return jsonify({"status": "opened"})
    return jsonify({"error": "No path"}), 400

@app.route('/stream')
def stream():
    def event_stream():
        while True:
            try:
                item = progress_queue.get(timeout=1.0)
                yield f"data: {json.dumps(item)}\n\n"
            except queue.Empty:
                yield ": ping\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    app.run(port=5000, debug=False)
