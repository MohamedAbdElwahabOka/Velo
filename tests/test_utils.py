import json
from pathlib import Path

import utils


def test_settings_defaults_are_merged(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "get_app_dir", lambda: tmp_path)
    (tmp_path / utils.SETTINGS_FILE).write_text(
        json.dumps({"download_folder": "D:/Media"}),
        encoding="utf-8",
    )

    settings = utils.load_settings()

    assert settings["download_folder"] == "D:/Media"
    assert settings["default_quality"] == "best"
    assert settings["default_format"] == "video"
    assert settings["network_mode"] == "stable"


def test_clear_history_empties_history_file(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "get_app_dir", lambda: tmp_path)
    (tmp_path / utils.HISTORY_FILE).write_text(
        json.dumps([{"title": "Example"}]),
        encoding="utf-8",
    )

    assert utils.clear_history() is True
    assert utils.load_history() == []


def test_history_stats_counts_files_channels_and_formats(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "get_app_dir", lambda: tmp_path)
    media = tmp_path / "video.mp4"
    media.write_bytes(b"12345")
    missing = tmp_path / "missing.mp3"
    history = [
        {
            "title": "Video",
            "channel": "Channel A",
            "filepath": str(media),
            "timestamp": "2026-05-17T10:00:00",
        },
        {
            "title": "Audio",
            "channel": "Channel A",
            "filepath": str(missing),
            "timestamp": "2026-05-17T11:00:00",
        },
    ]
    (tmp_path / utils.HISTORY_FILE).write_text(json.dumps(history), encoding="utf-8")

    stats = utils.get_history_stats()

    assert stats["total_items"] == 2
    assert stats["existing_files"] == 1
    assert stats["missing_files"] == 1
    assert stats["total_bytes"] == 5
    assert stats["channels"][0] == ("Channel A", 2)
    assert ("mp4", 1) in stats["formats"]
    assert stats["daily"][0] == ("2026-05-17", 2)
