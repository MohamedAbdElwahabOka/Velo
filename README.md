# Velo

Velo is a local media workspace for downloading videos, extracting audio, creating short clips, managing batch queues, and understanding download history through built-in statistics.

It is built for real-world connections, including unstable and low-bandwidth networks. The web dashboard runs locally in your browser and the backend is powered by Flask and yt-dlp.

## Highlights

- Local web dashboard with light/dark mode.
- Low-bandwidth network modes: Stable, Balanced, Turbo, and Data Saver.
- Single video, audio-only, batch download, and clip maker workflows.
- Queue controls: pause, resume, stop, retry failed items, dedupe links, and queue from history.
- Size estimate before download when the source provides format sizes.
- Statistics dashboard: total downloads, storage usage, file availability, top channels, formats, and daily activity.
- Reports export as JSON or CSV.
- Multilingual UI foundation with English and Arabic support.
- History search, channel filtering, path copy, reuse URL, and open file/folder actions.

## Requirements

- Python 3.11 or newer.
- FFmpeg installed and available on PATH.
- Internet access for downloading media and loading CDN assets used by the dashboard.

Install FFmpeg:

```powershell
winget install ffmpeg
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

The app opens at:

```text
http://127.0.0.1:5000
```

On Windows you can also run:

```powershell
.\run_velo.bat
```

## Recommended Settings For Weak Internet

- Use the `Low Bandwidth` preset for the smallest practical downloads.
- Use `Data Saver` when the connection disconnects often.
- Use `Stable` when downloads fail midway and need more retries.
- Use `Balanced` when the connection is slow but mostly steady.
- Use `Turbo` only when the connection can handle parallel fragments.

## API Overview

- `GET /api/meta`: app metadata and feature flags.
- `GET /api/settings`, `POST /api/settings`: read and save settings.
- `GET /api/history`, `DELETE /api/history`: read or clear history.
- `GET /api/stats`: computed statistics from local history.
- `GET /api/report?format=json|csv`: export reports.
- `POST /api/estimate`: estimate known source format sizes.
- `POST /api/fetch`: fetch video info.
- `POST /api/download`: start a single download.
- `POST /api/batch`: queue batch downloads.
- `GET /api/batch/state`: inspect batch state.
- `POST /api/batch/control`: pause, resume, stop, or retry failed jobs.
- `POST /api/clip`: generate a clip.

## Testing

```powershell
python -m pytest
```

The current tests focus on settings, history, and statistics helpers.

## Packaging Ideas

For a professional Windows release, package with PyInstaller:

```powershell
pip install pyinstaller
pyinstaller --onefile --name Velo main.py
```

After that, add an app icon, signed installer, release notes, and a versioned changelog.

## Font Assets

Arabic UI text uses locally bundled Thmanyah Sans `woff2` files from the Thmanyah Font Family package. If you distribute this app, keep the original font license available and confirm the package terms allow your distribution use case.

## Responsible Use

Only download media you are allowed to save and reuse. Velo does not bypass DRM or private access controls.
