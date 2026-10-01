"""Local append-only conversation journal. A crash cannot erase prior turns."""
import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock

_PATH = Path.home() / ".usama" / "conversation_journal.jsonl"
_LOCK = Lock()


def record_turn(role: str, text: str) -> None:
    if role not in ("user", "assistant") or not str(text).strip():
        return
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "role": role,
        "text": str(text).strip()[:4000],
    }
    with _LOCK:
        with _PATH.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())


def recent_context(limit: int = 16, budget: int = 5500) -> str:
    if not _PATH.exists():
        return ""
    with _LOCK:
        try:
            # Scan locally; return only a compact tail to the live model.
            lines = _PATH.read_text(encoding="utf-8").splitlines()[-max(1, limit):]
        except OSError:
            return ""
    entries = []
    for line in lines:
        try:
            row = json.loads(line)
            if row.get("role") in ("user", "assistant") and row.get("text"):
                entries.append(f"{row['role']}: {row['text']}")
        except (ValueError, TypeError, KeyError):
            continue
    if not entries:
        return ""
    selected = []
    size = 0
    for entry in reversed(entries):
        if size + len(entry) > budget:
            break
        selected.append(entry)
        size += len(entry)
    selected.reverse()
    return "[RECENT CONVERSATION TURNS — saved locally across restarts]\n" + "\n".join(selected) + "\n"
