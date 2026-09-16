from pathlib import Path

from session_history import (
    infer_subject_from_path,
    normalize_subject_id,
    parse_recording_number,
)


def test_session_history_helpers_handle_normalization_and_recording_paths(
    tmp_path: Path,
) -> None:
    recordings_root = tmp_path / "recordings"
    subject_dir = recordings_root / "Person 01"
    subject_dir.mkdir(parents=True)
    audio_path = subject_dir / "Person 01-recording003.wav"
    audio_path.write_bytes(b"")

    assert normalize_subject_id(" Person 01 ") == "person-01"
    assert parse_recording_number(audio_path) == 3
    assert infer_subject_from_path(audio_path, recordings_root) == "person-01"
