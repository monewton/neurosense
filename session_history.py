"""
NeuroSense AI - Session history and trend tracking (SQLite).

Stores each analysis run and compares scores to a rolling baseline.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from audio_utils import configure_stdio

DEFAULT_DB_PATH = Path("data") / "neurosense_history.db"

TREND_METRICS = (
    ("behavioral_score", "Behavioral Score", "higher"),
    ("stress_level", "Stress Level", "lower"),
    ("speech_ratio", "Speech Ratio", "higher"),
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_context_tag(tag: str | None) -> str | None:
    """Normalize a user-supplied context tag for storage and lookup."""
    if tag is None:
        return None
    cleaned = " ".join(tag.strip().split())
    if not cleaned:
        return None
    return cleaned[:80]


def normalize_subject_id(subject_id: str | None) -> str | None:
    """Normalize a subject identifier (e.g. person1, person-2)."""
    if subject_id is None:
        return None
    cleaned = subject_id.strip().lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", cleaned)
    cleaned = cleaned.strip("-_")
    if not cleaned:
        return None
    return cleaned[:64]


def parse_recording_number(path: Path | str) -> int | None:
    """Extract N from filenames like recording_003.wav or person1-recording3."""
    stem = Path(path).stem.lower()
    match = re.search(r"(?:^recording[_-]?|^.*-recording[_-]?)(\d+)$", stem)
    if match:
        return int(match.group(1))
    return None


def infer_subject_from_path(
    path: Path | str,
    recordings_root: Path | str = "recordings",
) -> str | None:
    """Infer subject id when a file lives under recordings/<subject>/..."""
    file_path = Path(path).resolve()
    root = Path(recordings_root).resolve()
    try:
        relative = file_path.relative_to(root)
    except ValueError:
        return None
    if len(relative.parts) >= 2:
        return normalize_subject_id(relative.parts[0])
    return None


def subject_recordings_dir(
    subject_id: str,
    recordings_root: Path | str = "recordings",
) -> Path:
    subject_id = normalize_subject_id(subject_id)
    if not subject_id:
        raise ValueError("subject_id is required")
    folder = Path(recordings_root) / subject_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _session_filters(
    *,
    subject_id: str | None = None,
    context_tag: str | None = None,
    prefix: str = "WHERE",
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if subject_id is not None:
        clauses.append("subject_id = ?")
        params.append(subject_id)
    if context_tag is not None:
        clauses.append("context_tag = ?")
        params.append(context_tag)
    if not clauses:
        return "", []
    return f"{prefix} {' AND '.join(clauses)}", params


def _connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            source_file TEXT NOT NULL,
            duration_sec REAL,
            sample_rate INTEGER,
            subject_id TEXT,
            recording_number INTEGER,
            scenario TEXT,
            context_tag TEXT,
            pipeline TEXT NOT NULL,
            behavioral_score INTEGER,
            stress_level INTEGER,
            speech_ratio REAL,
            rms_energy REAL,
            pitch_variation REAL,
            speaking_rate REAL,
            claude_status TEXT,
            claude_confidence TEXT
        )
        """
    )
    _ensure_column(conn, "sessions", "subject_id", "TEXT")
    _ensure_column(conn, "sessions", "recording_number", "INTEGER")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_recorded_at ON sessions(recorded_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_context_tag ON sessions(context_tag)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_subject_id ON sessions(subject_id)"
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_subject_recording
        ON sessions(subject_id, recording_number)
        """
    )
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_def: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")


def _max_recording_number_on_disk(subject_id: str, recordings_root: Path | str) -> int:
    folder = Path(recordings_root) / subject_id
    if not folder.is_dir():
        return 0
    highest = 0
    patterns = ("recording_*.wav", "recording-*.wav", "*-recording*.wav", "*.wav")
    seen: set[Path] = set()
    for pattern in patterns:
        for path in folder.glob(pattern):
            if path in seen:
                continue
            seen.add(path)
            number = parse_recording_number(path)
            if number is not None:
                highest = max(highest, number)
    return highest


def peek_next_recording_number(
    subject_id: str,
    *,
    recordings_root: Path | str = "recordings",
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Return the next recording number for a subject (DB + on-disk files)."""
    subject_id = normalize_subject_id(subject_id)
    if not subject_id:
        raise ValueError("subject_id is required")

    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT MAX(recording_number) FROM sessions WHERE subject_id = ?",
            (subject_id,),
        ).fetchone()
        max_db = int(row[0] or 0)

    max_disk = _max_recording_number_on_disk(subject_id, recordings_root)
    return max(max_db, max_disk) + 1


def next_recording_path(
    subject_id: str,
    recordings_root: Path | str = "recordings",
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> Path:
    """Path for the next numbered recording for a subject."""
    subject_id = normalize_subject_id(subject_id)
    if not subject_id:
        raise ValueError("subject_id is required")
    number = peek_next_recording_number(
        subject_id,
        recordings_root=recordings_root,
        db_path=db_path,
    )
    return subject_recordings_dir(subject_id, recordings_root) / f"recording_{number:03d}.wav"


def resolve_subject_id(
    subject_id: str | None,
    source_path: Path | str,
) -> str | None:
    """Use explicit subject id or infer it from the recording path."""
    normalized = normalize_subject_id(subject_id)
    if normalized:
        return normalized
    return infer_subject_from_path(source_path)


def _resolve_recording_number(
    conn: sqlite3.Connection,
    subject_id: str | None,
    source_path: Path | str,
    recordings_root: Path | str = "recordings",
) -> int | None:
    if not subject_id:
        return None

    parsed = parse_recording_number(source_path)
    if parsed is not None:
        return parsed

    row = conn.execute(
        "SELECT MAX(recording_number) FROM sessions WHERE subject_id = ?",
        (subject_id,),
    ).fetchone()
    max_db = int(row[0] or 0)
    max_disk = _max_recording_number_on_disk(subject_id, recordings_root)
    return max(max_db, max_disk) + 1


def save_session(
    features: dict,
    source_path: Path | str,
    *,
    duration_sec: float | None = None,
    sample_rate: int | None = None,
    pipeline: str = "analyzer",
    scenario: str | None = None,
    subject_id: str | None = None,
    context_tag: str | None = None,
    claude_analysis: dict | None = None,
    recordings_root: Path | str = "recordings",
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Persist one analysis session. Returns saved session metadata."""
    source = str(Path(source_path))
    context_tag = normalize_context_tag(context_tag)
    subject_id = resolve_subject_id(subject_id, source_path)
    claude_status = None
    claude_confidence = None
    if claude_analysis and "error" not in claude_analysis:
        claude_status = claude_analysis.get("status")
        claude_confidence = claude_analysis.get("confidence")

    with _connect(db_path) as conn:
        recording_number = _resolve_recording_number(
            conn,
            subject_id,
            source_path,
            recordings_root=recordings_root,
        )
        cursor = conn.execute(
            """
            INSERT INTO sessions (
                recorded_at, source_file, duration_sec, sample_rate,
                subject_id, recording_number,
                scenario, context_tag, pipeline,
                behavioral_score, stress_level, speech_ratio,
                rms_energy, pitch_variation, speaking_rate,
                claude_status, claude_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now_iso(),
                source,
                duration_sec,
                sample_rate,
                subject_id,
                recording_number,
                scenario,
                context_tag,
                pipeline,
                int(features.get("behavioral_score", 0)),
                int(features.get("stress_level", 0)),
                float(features.get("speech_ratio", 0)),
                float(features.get("rms_energy", 0)),
                float(features.get("pitch_variation", 0)),
                float(features.get("speaking_rate", 0)),
                claude_status,
                claude_confidence,
            ),
        )
        conn.commit()
        session_id = int(cursor.lastrowid)

    return {
        "id": session_id,
        "subject_id": subject_id,
        "recording_number": recording_number,
        "source_file": source,
    }


def get_baseline(
    days: int = 7,
    *,
    before: datetime | None = None,
    subject_id: str | None = None,
    context_tag: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """
    Rolling baseline averages for the last N days.
    Uses sessions strictly before `before` (defaults to now).
    """
    end = before or datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    start_iso = start.replace(microsecond=0).isoformat()
    end_iso = end.replace(microsecond=0).isoformat()
    subject_id = normalize_subject_id(subject_id)
    context_tag = normalize_context_tag(context_tag)

    query = """
        SELECT
            COUNT(*) AS session_count,
            AVG(behavioral_score) AS avg_behavioral_score,
            AVG(stress_level) AS avg_stress_level,
            AVG(speech_ratio) AS avg_speech_ratio,
            AVG(rms_energy) AS avg_rms_energy,
            AVG(pitch_variation) AS avg_pitch_variation,
            AVG(speaking_rate) AS avg_speaking_rate
        FROM sessions
        WHERE recorded_at >= ? AND recorded_at < ?
    """
    params: list[Any] = [start_iso, end_iso]
    filter_sql, filter_params = _session_filters(
        subject_id=subject_id,
        context_tag=context_tag,
        prefix="AND",
    )
    query += f" {filter_sql}"
    params.extend(filter_params)

    with _connect(db_path) as conn:
        row = conn.execute(query, params).fetchone()

    count = int(row["session_count"] or 0)
    return {
        "days": days,
        "subject_id": subject_id,
        "context_tag": context_tag,
        "session_count": count,
        "avg_behavioral_score": row["avg_behavioral_score"],
        "avg_stress_level": row["avg_stress_level"],
        "avg_speech_ratio": row["avg_speech_ratio"],
        "avg_rms_energy": row["avg_rms_energy"],
        "avg_pitch_variation": row["avg_pitch_variation"],
        "avg_speaking_rate": row["avg_speaking_rate"],
    }


def compare_to_baseline(
    features: dict,
    days: int = 7,
    *,
    subject_id: str | None = None,
    context_tag: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Compare current feature values to the rolling baseline."""
    baseline = get_baseline(
        days,
        subject_id=subject_id,
        context_tag=context_tag,
        db_path=db_path,
    )
    comparisons: dict[str, dict[str, Any]] = {}

    current_values = {
        "behavioral_score": float(features.get("behavioral_score", 0)),
        "stress_level": float(features.get("stress_level", 0)),
        "speech_ratio": float(features.get("speech_ratio", 0)),
    }
    baseline_keys = {
        "behavioral_score": "avg_behavioral_score",
        "stress_level": "avg_stress_level",
        "speech_ratio": "avg_speech_ratio",
    }

    for metric, _, direction in TREND_METRICS:
        avg = baseline.get(baseline_keys[metric])
        current = current_values[metric]
        if avg is None or baseline["session_count"] == 0:
            comparisons[metric] = {
                "current": current,
                "average": None,
                "delta": None,
                "direction": direction,
                "interpretation": "no baseline yet",
            }
            continue

        delta = current - avg
        if direction == "higher":
            if delta > 0:
                interpretation = "above average (positive)"
            elif delta < 0:
                interpretation = "below average"
            else:
                interpretation = "at average"
        else:
            if delta < 0:
                interpretation = "below average (positive)"
            elif delta > 0:
                interpretation = "above average"
            else:
                interpretation = "at average"

        comparisons[metric] = {
            "current": current,
            "average": avg,
            "delta": delta,
            "direction": direction,
            "interpretation": interpretation,
        }

    return {"baseline": baseline, "comparisons": comparisons}


def _format_delta(metric: str, delta: float | None) -> str:
    if delta is None:
        return "n/a"
    if metric == "speech_ratio":
        return f"{delta:+.1%}"
    return f"{delta:+.1f}"


def print_trend_summary(
    features: dict,
    *,
    days: int = 7,
    subject_id: str | None = None,
    context_tag: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Print current scores vs rolling baseline."""
    subject_id = normalize_subject_id(subject_id)
    context_tag = normalize_context_tag(context_tag)
    result = compare_to_baseline(
        features,
        days=days,
        subject_id=subject_id,
        context_tag=context_tag,
        db_path=db_path,
    )
    baseline = result["baseline"]
    comparisons = result["comparisons"]

    print("=" * 60)
    title_parts = [f"📈 TREND vs {days}-DAY AVERAGE"]
    if subject_id:
        title_parts.append(f"subject: {subject_id}")
    if context_tag:
        title_parts.append(f"tag: {context_tag}")
    print("  ".join(title_parts))
    print("=" * 60)

    if baseline["session_count"] == 0:
        print()
        if subject_id and context_tag:
            print(
                f"   No prior sessions for {subject_id!r} with tag {context_tag!r} "
                f"in the last {days} days."
            )
        elif subject_id:
            print(f"   No prior sessions for {subject_id!r} in the last {days} days.")
        elif context_tag:
            print(
                f"   No prior sessions with tag {context_tag!r} in the last {days} days."
            )
        else:
            print(f"   No prior sessions in the last {days} days — baseline starts next run.")
        print()
        return

    print(f"   Baseline sessions: {baseline['session_count']}")
    print()

    labels = {key: label for key, label, _ in TREND_METRICS}
    for metric, comp in comparisons.items():
        label = labels[metric]
        current = comp["current"]
        average = comp["average"]
        delta = comp["delta"]

        if metric == "speech_ratio":
            current_str = f"{current:.1%}"
            avg_str = f"{average:.1%}" if average is not None else "n/a"
        else:
            current_str = f"{current:.0f}"
            avg_str = f"{average:.1f}" if average is not None else "n/a"

        print(f"   {label}: {current_str}  (avg {avg_str}, {_format_delta(metric, delta)})")
        print(f"      → {comp['interpretation']}")
        print()


def list_sessions(
    limit: int = 20,
    *,
    subject_id: str | None = None,
    context_tag: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[sqlite3.Row]:
    subject_id = normalize_subject_id(subject_id)
    context_tag = normalize_context_tag(context_tag)
    query = "SELECT * FROM sessions"
    filter_sql, params = _session_filters(
        subject_id=subject_id,
        context_tag=context_tag,
    )
    query += f" {filter_sql}" if filter_sql else ""
    query += " ORDER BY recorded_at DESC LIMIT ?"
    params.append(limit)

    with _connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return list(rows)


def list_subjects(*, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                subject_id,
                COUNT(*) AS session_count,
                MAX(recorded_at) AS last_recorded_at,
                MAX(recording_number) AS latest_recording_number,
                AVG(behavioral_score) AS avg_behavioral_score,
                AVG(stress_level) AS avg_stress_level
            FROM sessions
            WHERE subject_id IS NOT NULL
            GROUP BY subject_id
            ORDER BY subject_id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def print_subjects(*, db_path: Path = DEFAULT_DB_PATH) -> None:
    subjects = list_subjects(db_path=db_path)

    print("=" * 60)
    print("👤 SUBJECTS")
    print("=" * 60)

    if not subjects:
        print()
        print("   No subject-linked sessions yet.")
        print('   Example: python simple_recorder.py --subject person1')
        print()
        return

    print()
    for row in subjects:
        latest = row["latest_recording_number"]
        latest_label = f"recording #{latest}" if latest else "no numbered recordings"
        print(f"   {row['subject_id']}  ({row['session_count']} session(s), {latest_label})")
        print(
            f"       Last activity: {row['last_recorded_at'][:19].replace('T', ' ')}  |  "
            f"Avg score {row['avg_behavioral_score']:.1f}  |  "
            f"Avg stress {row['avg_stress_level']:.1f}"
        )
        print()


def get_tag_summaries(
    days: int = 7,
    *,
    subject_id: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Average scores grouped by context tag for the rolling window."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    start_iso = start.replace(microsecond=0).isoformat()
    end_iso = end.replace(microsecond=0).isoformat()
    subject_id = normalize_subject_id(subject_id)

    query = """
        SELECT
            COALESCE(context_tag, '(untagged)') AS tag_label,
            context_tag,
            COUNT(*) AS session_count,
            AVG(behavioral_score) AS avg_behavioral_score,
            AVG(stress_level) AS avg_stress_level,
            AVG(speech_ratio) AS avg_speech_ratio
        FROM sessions
        WHERE recorded_at >= ? AND recorded_at < ?
    """
    params: list[Any] = [start_iso, end_iso]
    filter_sql, filter_params = _session_filters(subject_id=subject_id, prefix="AND")
    query += f" {filter_sql}"
    params.extend(filter_params)
    query += """
        GROUP BY context_tag
        ORDER BY session_count DESC, tag_label ASC
    """

    with _connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def print_tag_summaries(
    days: int = 7,
    *,
    subject_id: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Print score averages grouped by context tag."""
    subject_id = normalize_subject_id(subject_id)
    summaries = get_tag_summaries(days=days, subject_id=subject_id, db_path=db_path)

    print("=" * 60)
    if subject_id:
        print(f"🏷️  SCORES BY CONTEXT TAG — {subject_id} (last {days} days)")
    else:
        print(f"🏷️  SCORES BY CONTEXT TAG (last {days} days)")
    print("=" * 60)

    if not summaries:
        print()
        print("   No tagged sessions in this window yet.")
        print("   Example: python audio_analyzer.py --tag \"after work\"")
        print()
        return

    print()
    for row in summaries:
        print(f"   {row['tag_label']}  ({row['session_count']} session(s))")
        print(
            f"       Avg score {row['avg_behavioral_score']:.1f}  |  "
            f"Avg stress {row['avg_stress_level']:.1f}  |  "
            f"Avg speech {row['avg_speech_ratio']:.1%}"
        )
        print()


def _format_session_label(row: sqlite3.Row) -> str:
    if row["subject_id"] and row["recording_number"]:
        return f"{row['subject_id']} recording #{row['recording_number']}"
    if row["subject_id"]:
        return str(row["subject_id"])
    return Path(row["source_file"]).name


def print_history(
    limit: int = 20,
    *,
    subject_id: str | None = None,
    context_tag: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Print recent session history."""
    subject_id = normalize_subject_id(subject_id)
    context_tag = normalize_context_tag(context_tag)
    rows = list_sessions(
        limit=limit,
        subject_id=subject_id,
        context_tag=context_tag,
        db_path=db_path,
    )

    print("=" * 60)
    title = f"📋 SESSION HISTORY (last {limit})"
    if subject_id:
        title = f"📋 SESSION HISTORY — {subject_id} (last {limit})"
    if context_tag:
        title += f"  [tag: {context_tag}]"
    print(title)
    print("=" * 60)

    if not rows:
        print()
        print("   No sessions recorded yet.")
        print("   Run audio_analyzer.py or claude_demo.py to create entries.")
        print()
        return

    print()
    for row in rows:
        ts = row["recorded_at"][:19].replace("T", " ")
        label = _format_session_label(row)
        print(f"   [{row['id']}] {ts}  {label}")
        print(
            f"       Score {row['behavioral_score']}/100  |  "
            f"Stress {row['stress_level']}/100  |  "
            f"Speech {row['speech_ratio']:.1%}  |  "
            f"{row['pipeline']}"
        )
        if row["context_tag"]:
            print(f"       Tag: {row['context_tag']}")
        if row["claude_status"]:
            print(f"       Claude: {row['claude_status']} ({row['claude_confidence']})")
        print()


def print_saved_session(saved: dict[str, Any]) -> None:
    """Print a one-line confirmation after saving a session."""
    if saved.get("subject_id") and saved.get("recording_number"):
        print(
            f"💾 Saved session #{saved['id']}: "
            f"{saved['subject_id']} recording #{saved['recording_number']}"
        )
    elif saved.get("subject_id"):
        print(f"💾 Saved session #{saved['id']}: subject {saved['subject_id']}")
    else:
        print(f"💾 Saved session #{saved['id']}")


def _main() -> None:
    configure_stdio()
    parser = argparse.ArgumentParser(
        description="View NeuroSense session history and trends.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of recent sessions to show (default: 20)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Rolling baseline window in days (default: 7)",
    )
    parser.add_argument(
        "--tag",
        metavar="LABEL",
        help="Filter history to sessions with this context tag",
    )
    parser.add_argument(
        "--subject",
        metavar="ID",
        help="Filter history to one subject (e.g. person1)",
    )
    parser.add_argument(
        "--subjects",
        action="store_true",
        help="List all tracked subjects",
    )
    parser.add_argument(
        "--tags",
        action="store_true",
        help="Show score averages grouped by context tag",
    )
    args = parser.parse_args()
    subject_id = normalize_subject_id(args.subject)
    context_tag = normalize_context_tag(args.tag)

    if args.subjects:
        print_subjects()
        return

    if args.tags:
        print_tag_summaries(days=args.days, subject_id=subject_id)
        return

    print_history(limit=args.limit, subject_id=subject_id, context_tag=context_tag)
    baseline = get_baseline(days=args.days, subject_id=subject_id, context_tag=context_tag)
    print("=" * 60)
    baseline_title = f"📊 {args.days}-DAY BASELINE"
    if subject_id:
        baseline_title += f" — {subject_id}"
    if context_tag:
        baseline_title += f"  [tag: {context_tag}]"
    print(baseline_title)
    print("=" * 60)
    print()
    if baseline["session_count"] == 0:
        print("   No sessions in this window yet.")
    else:
        print(f"   Sessions: {baseline['session_count']}")
        print(f"   Avg Behavioral Score: {baseline['avg_behavioral_score']:.1f}")
        print(f"   Avg Stress Level: {baseline['avg_stress_level']:.1f}")
        print(f"   Avg Speech Ratio: {baseline['avg_speech_ratio']:.1%}")
    print()


if __name__ == "__main__":
    _main()
