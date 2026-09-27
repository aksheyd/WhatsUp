from __future__ import annotations

import threading
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from .paths import RAW
from .schema import RawExcerpt


def write_text_atomic(path: Path, text: str) -> None:
    """Replace a file in one step, so an interrupted run never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def raw_path(code: str, place_id: str) -> Path:
    return RAW / code / f"{place_id}.json"


def load_raw(code: str, place_id: str) -> RawExcerpt | None:
    path = raw_path(code, place_id)
    if not path.exists():
        return None
    return RawExcerpt.model_validate_json(path.read_text(encoding="utf-8"))


def save_raw(raw: RawExcerpt) -> None:
    write_text_atomic(raw_path(raw.state, raw.placeId), raw.model_dump_json(indent=2) + "\n")


class Failure(BaseModel):
    tries: int
    reason: str
    error: str


FAILURE_LOG = TypeAdapter(dict[str, Failure])


class Failures:
    """Failure counts kept between runs, so places that keep failing get skipped."""

    def __init__(self, path: Path, *, max_tries: int) -> None:
        self._path = path
        self._max_tries = max_tries
        self._lock = threading.Lock()
        self._records = FAILURE_LOG.validate_json(path.read_bytes()) if path.exists() else {}

    def exhausted(self, key: str) -> bool:
        record = self._records.get(key)
        return record is not None and record.tries >= self._max_tries

    def exhausted_count(self) -> int:
        return sum(1 for key in self._records if self.exhausted(key))

    def record(self, key: str, reason: str, error: Exception) -> int:
        with self._lock:
            previous = self._records.get(key)
            tries = (previous.tries if previous else 0) + 1
            self._records[key] = Failure(tries=tries, reason=reason, error=str(error)[:300])
            self._save()
            return tries

    def clear(self, key: str) -> None:
        with self._lock:
            if self._records.pop(key, None) is not None:
                self._save()

    def _save(self) -> None:
        write_text_atomic(self._path, FAILURE_LOG.dump_json(self._records, indent=2).decode() + "\n")
