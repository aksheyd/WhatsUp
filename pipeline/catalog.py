from __future__ import annotations

import csv
from pathlib import Path

from .paths import PUBLISHED, URLS
from .schema import Place, StateFile, slugify
from .store import write_text_atomic

STATE_NAMES: dict[str, str] = {
    "al": "Alabama",
    "ak": "Alaska",
    "az": "Arizona",
    "ar": "Arkansas",
    "ca": "California",
    "co": "Colorado",
    "ct": "Connecticut",
    "de": "Delaware",
    "fl": "Florida",
    "ga": "Georgia",
    "hi": "Hawaii",
    "id": "Idaho",
    "il": "Illinois",
    "in": "Indiana",
    "ia": "Iowa",
    "ks": "Kansas",
    "ky": "Kentucky",
    "la": "Louisiana",
    "me": "Maine",
    "md": "Maryland",
    "ma": "Massachusetts",
    "mi": "Michigan",
    "mn": "Minnesota",
    "ms": "Mississippi",
    "mo": "Missouri",
    "mt": "Montana",
    "ne": "Nebraska",
    "nv": "Nevada",
    "nh": "New Hampshire",
    "nj": "New Jersey",
    "nm": "New Mexico",
    "ny": "New York",
    "nc": "North Carolina",
    "nd": "North Dakota",
    "oh": "Ohio",
    "ok": "Oklahoma",
    "or": "Oregon",
    "pa": "Pennsylvania",
    "ri": "Rhode Island",
    "sc": "South Carolina",
    "sd": "South Dakota",
    "tn": "Tennessee",
    "tx": "Texas",
    "ut": "Utah",
    "vt": "Vermont",
    "va": "Virginia",
    "wa": "Washington",
    "wv": "West Virginia",
    "wi": "Wisconsin",
    "wy": "Wyoming",
}


def load_places_from_csv(code: str) -> list[Place]:
    path = URLS / f"{code}_county_urls.csv"
    if not path.exists():
        return []
    places: dict[str, Place] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("county") or "").strip()
            place_id = slugify(name)
            if name and place_id not in places:
                places[place_id] = Place(id=place_id, name=name, sourceIndex=(row.get("url") or "").strip())
    return list(places.values())


def published_path(code: str) -> Path:
    return PUBLISHED / f"{code}.json"


def published_codes() -> list[str]:
    return sorted(path.stem for path in PUBLISHED.glob("*.json"))


def load_state_file(code: str) -> StateFile | None:
    path = published_path(code)
    if not path.exists():
        return None
    return StateFile.model_validate_json(path.read_text(encoding="utf-8"))


def save_state_file(state: StateFile) -> None:
    write_text_atomic(published_path(state.state), state.model_dump_json(indent=2) + "\n")


def build_catalog(codes: list[str] | None = None) -> list[str]:
    """Write one state file per state from the URL lists, keeping questions already written."""
    targets = codes or sorted(path.name.removesuffix("_county_urls.csv") for path in URLS.glob("*_county_urls.csv"))
    for code in targets:
        existing = load_state_file(code)
        prior = {place.id: place for place in existing.places} if existing else {}
        places = load_places_from_csv(code)
        for place in places:
            if old := prior.get(place.id):
                place.questions = old.questions
                place.sourceIndex = place.sourceIndex or old.sourceIndex
        save_state_file(StateFile(state=code, stateName=STATE_NAMES.get(code, code.upper()), places=places))
    return targets
