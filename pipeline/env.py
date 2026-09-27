from __future__ import annotations

import os

from .paths import ROOT


def load_dotenv() -> None:
    """Copy KEY=value lines from the repo's .env into the environment without overriding real variables."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        key = key.strip()
        if not sep or not key or key.startswith("#"):
            continue
        os.environ.setdefault(key, value.strip().strip("'\""))
