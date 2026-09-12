"""Shared audio I/O helpers for NeuroSense AI."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SOUNDFILE_SUFFIXES = frozenset({".wav", ".flac", ".ogg", ".oga", ".aiff", ".aif"})

LIBROSA_SUFFIXES = frozenset(
    {
        ".mp3",
        ".m4a",
        ".mp4",
        ".aac",
        ".opus",
        ".webm",
        ".mpeg",
        ".mpga",
    }
)


def configure_stdio() -> None:
    """Avoid UnicodeEncodeError on Windows consoles (cp1252) when printing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError, OSError):
                pass


def _to_mono(raw: np.ndarray) -> np.ndarray:
    """Shape (samples, channels) -> mono (samples,)."""
    if raw.ndim == 1:
        return raw.astype(np.float64, copy=False)
    if raw.shape[1] == 1:
        return raw[:, 0].astype(np.float64, copy=False)
    return np.mean(raw, axis=1).astype(np.float64)


def _load_soundfile(path: Path) -> tuple[np.ndarray, int]:
    raw, sr = sf.read(path, always_2d=True, dtype="float64")
    return _to_mono(raw), int(sr)


def _load_librosa(path: Path) -> tuple[np.ndarray, int]:
    try:
        import librosa
    except ImportError as e:
        raise RuntimeError(
            "Loading this format needs librosa and ffmpeg on your PATH.\n"
            "  pip install librosa\n"
            "Install ffmpeg: https://ffmpeg.org/download.html"
        ) from e
    try:
        y, sr = librosa.load(str(path), sr=None, mono=False)
    except Exception as e:
        raise RuntimeError(
            "librosa could not decode this file. For MP3/M4A/Opus/WebM, install ffmpeg "
            "and add it to your PATH, then retry.\n"
            f"Detail: {type(e).__name__}: {e}"
        ) from e
    if y.ndim == 2:
        y = np.mean(y, axis=0)
    return y.astype(np.float64), int(sr)


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    """
    Load audio as mono float64, sample rate Hz.
    Lossless (WAV/FLAC/OGG/AIFF): soundfile.
    Compressed (MP3/M4A/Opus/WebM/…): librosa + ffmpeg.
    """
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")

    suffix = path.suffix.lower()

    if suffix in LIBROSA_SUFFIXES:
        return _load_librosa(path)

    if suffix in SOUNDFILE_SUFFIXES:
        return _load_soundfile(path)

    try:
        return _load_soundfile(path)
    except Exception:
        pass

    try:
        return _load_librosa(path)
    except RuntimeError:
        raise
    except Exception as e:
        raise ValueError(
            f"Could not read {path.name!r} (unknown or unsupported format). "
            "Try MP3, M4A, FLAC, or OGG; for compressed formats install librosa + ffmpeg."
        ) from e


def pick_default_audio(
    recordings_folder: Path | str = "recordings",
    *,
    subject_id: str | None = None,
) -> Path:
    """Newest supported audio file under recordings/ (optionally scoped to one subject)."""
    from session_history import normalize_subject_id

    folder = Path(recordings_folder)
    search_roots = []
    normalized_subject = normalize_subject_id(subject_id)
    if normalized_subject:
        subject_folder = folder / normalized_subject
        if subject_folder.is_dir():
            search_roots.append(subject_folder)
        else:
            raise FileNotFoundError(
                f"No recordings folder for subject {normalized_subject!r} under {folder}/"
            )
    else:
        search_roots.append(folder)
        search_roots.extend(p for p in folder.iterdir() if p.is_dir())

    patterns = (
        "*.mp3",
        "*.m4a",
        "*.aac",
        "*.opus",
        "*.webm",
        "*.flac",
        "*.ogg",
        "*.oga",
        "*.wav",
        "*.aiff",
        "*.aif",
    )
    files: list[Path] = []
    for root in search_roots:
        for pattern in patterns:
            files.extend(root.glob(pattern))

    if not files:
        if normalized_subject:
            raise FileNotFoundError(
                f"No recordings found for subject {normalized_subject!r} under {folder}/"
            )
        raise FileNotFoundError(
            "No recordings found. Pass a file path or place audio under ./recordings/"
        )
    return max(files, key=lambda p: p.stat().st_mtime)
