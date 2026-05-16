# SnagTube 🚀

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)

**SnagTube** is a sleek, modern desktop application built with Python and CustomTkinter that lets you effortlessly download YouTube videos and audio for offline enjoyment.

---

## ✨ Features

- 🎨 **Modern GUI**: A beautiful, responsive interface with Dark Mode support.
- 📺 **High Definition**: Download videos in 1080p, 720p, or the best available quality.
- 🎵 **Audio Mode**: Extract high-quality MP3s with a single click.
- ⚡ **Background Processing**: Multi-threaded downloads keep the UI smooth and responsive.
- 📊 **Real-time Stats**: Track download speed, remaining time (ETA), and progress.
- 🕒 **History**: Quickly access your previous downloads from the built-in history tab.
- 🛠️ **Playlist Control**: Opt to download only the single video even if it's part of a playlist.
- 💻 **Cross-Platform**: Seamlessly runs on Windows, macOS, and Linux.

---

## 🛠️ Prerequisites

1.  **Python 3.11+**: [Download here](https://www.python.org/downloads/).
2.  **FFmpeg**: Essential for merging video/audio and processing MP3s.

### Installing FFmpeg

- **Windows**: Use `winget install ffmpeg` or download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

---

## 🚀 Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/yourusername/SnagTube.git
    cd SnagTube
    ```

2.  **Setup Virtual Environment** (Recommended):
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

---

## 📖 Usage

1.  Launch the app:
    ```bash
    python main.py
    ```
2.  **Paste** your YouTube link into the URL field.
3.  Click **Fetch Info** to see video details.
4.  Configure your **Format** (Video/Audio) and **Quality**.
5.  Hit **Download** and let SnagTube handle the rest!

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

Check out our [CONTRIBUTING.md](CONTRIBUTING.md) to get started!

---

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

## ⚠️ Disclaimer

> [!CAUTION]
> **This tool is for personal use only.**
> Please respect YouTube's Terms of Service and copyright laws. Only download content you have permission to access. SnagTube does not bypass DRM or download private/restricted content. The developers are not responsible for misuse of this software.
