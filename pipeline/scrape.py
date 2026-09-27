from __future__ import annotations

import csv
import re
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NamedTuple
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from . import excerpt
from .catalog import load_state_file
from .paths import RAW, URLS
from .schema import Place, RawExcerpt, slugify
from .store import Failures, load_raw, save_raw

USER_AGENT = "WhatsUpQuizBot/1.0 (+https://github.com/aksheyd/whatsup; educational excerpts)"
BLOCKED_STATUSES = frozenset({403, 429})
BODY_SELECTOR = ".chunk-content, .codes-chunks-pg"
NODE_LINK_SELECTOR = 'a[href*="nodeId="], a[href*="nodeid="]'
FAILURES_PATH = RAW / "scrape_status.json"
MAX_TRIES = 2
BLOCK_LIMIT = 5

NUMERIC_NODE = re.compile(r"nodeid=\d+$", re.I)
SKIP_TITLE = re.compile(
    r"supplement history|state law reference|comparative table|code of ordinances|"
    r"table of contents|preface|adoption ordinance|code comparative|"
    r"statutory reference|ordinance list and disposition",
    re.I,
)
CIVIC_TITLE = re.compile(
    r"\banimals?\b|\bdogs?\b|\bcats?\b|fowl|livestock|noise|nuisance|parking|"
    r"traffic|\bsnow\b|sidewalk|\bsigns?\b|\byard\b|weed|grass|garbage|refuse|"
    r"trash|litter|chicken|\bbees?\b|fireworks|curfew|alcohol|beverage|tobacco|"
    r"short.?term|rental|zoning|land use|bicycle|skate|\bparks?\b|\btrees?\b|fence|"
    r"\bpool\b|barbecue|\bbbq\b|public grounds|open space",
    re.I,
)
CHAPTER_TITLE = re.compile(r"^(title|chapter|article|part)\b", re.I)
DULL_TITLE = re.compile(r"administration|general provisions|personnel|finance", re.I)

GapReason = Literal["no_toc", "no_rank", "no_body", "thin"]


class BlockedError(RuntimeError):
    """The library answered 403 or 429."""


class GapError(RuntimeError):
    """A place gave no usable ordinance text."""

    def __init__(self, reason: GapReason, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class Link(NamedTuple):
    url: str
    title: str


@dataclass(frozen=True)
class Section:
    url: str
    title: str
    score: float


def clean_title(text: str) -> str:
    return " ".join(text.split())


def node_id(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    return (query.get("nodeId") or query.get("nodeid") or [""])[0]


def section_score(url: str, title: str) -> float:
    """Rank a code section by how likely it is to hold everyday rules like parking or pets."""
    node = node_id(url)
    score = 0.0
    if node.isdigit() or NUMERIC_NODE.search(url):
        score -= 100
    elif SKIP_TITLE.search(title):
        score -= 50
    if CIVIC_TITLE.search(title):
        score += 20
    if CHAPTER_TITLE.search(title):
        score += 2
    if DULL_TITLE.search(title):
        score -= 4
    return score + min(len(node), 12) / 12


def toc_csv_path(code: str, place_name: str) -> Path:
    return URLS / code / f"{place_name.replace(' ', '_')}_specific_urls.csv"


def find_toc_csv(code: str, place_name: str) -> Path | None:
    exact = toc_csv_path(code, place_name)
    if exact.exists():
        return exact
    wanted = slugify(place_name)
    for path in exact.parent.glob("*_specific_urls.csv"):
        if slugify(path.name.removesuffix("_specific_urls.csv").replace("_", " ")) == wanted:
            return path
    return None


def rank_sections(code: str, place_name: str) -> list[Section]:
    path = find_toc_csv(code, place_name)
    if path is None:
        return []
    sections: list[Section] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            url = (row.get("url") or "").strip()
            title = clean_title(row.get("link_text") or "")
            if url:
                sections.append(Section(url=url, title=title, score=section_score(url, title)))
    return sorted(sections, key=lambda section: -section.score)


def write_toc_csv(code: str, place_name: str, links: Iterable[Link]) -> Path:
    path = toc_csv_path(code, place_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["county", "url", "link_text"])
        writer.writerows([place_name, link.url, link.title] for link in links)
    return path


def extract_text(html: str) -> str:
    """Return the ordinance body text, skipping the library's menus and share buttons."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    for selector in (".chunk-content", ".codes-chunks-pg"):
        parts = [text for node in soup.select(selector) if (text := node.get_text(" ", strip=True))]
        if parts:
            return "\n\n".join(parts)
    return ""


def page_links(html: str, base_url: str) -> list[Link]:
    soup = BeautifulSoup(html, "html.parser")
    links: dict[str, Link] = {}
    for anchor in soup.find_all("a", href=True):
        url = urljoin(base_url, str(anchor["href"]))
        if url not in links:
            links[url] = Link(url=url, title=clean_title(anchor.get_text(" ", strip=True)))
    return list(links.values())


@contextmanager
def browser_page() -> Iterator[Page]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            yield browser.new_page(user_agent=USER_AGENT)
        finally:
            browser.close()


def goto(page: Page, url: str) -> None:
    response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    if response is not None and response.status in BLOCKED_STATUSES:
        raise BlockedError(f"blocked ({response.status}) on {url}")


def fetch_text(page: Page, url: str) -> str:
    try:
        goto(page, url)
        page.wait_for_selector(BODY_SELECTOR, timeout=25_000)
    except PlaywrightTimeoutError as exc:
        raise GapError("no_body", f"no ordinance body on {url}") from exc
    return extract_text(page.content())


def harvest_toc(page: Page, source_index: str) -> list[Link]:
    """Find a place's code on the library and collect the links to its sections."""
    base = source_index.rstrip("/")
    goto(page, base)
    page.wait_for_timeout(1500)
    code_pages = [
        link.url.split("?")[0].rstrip("/") for link in page_links(page.content(), page.url) if "/codes/" in link.url
    ]
    candidates = [f"{base}/codes/code_of_ordinances", f"{base}/codes/municipal_code", *code_pages, base]
    best: list[Link] = []
    for url in dict.fromkeys(candidates):
        goto(page, url)
        try:
            page.wait_for_selector(NODE_LINK_SELECTOR, timeout=20_000)
        except PlaywrightTimeoutError:
            continue
        page.wait_for_timeout(1500)
        links = [link for link in page_links(page.content(), page.url) if link.title and node_id(link.url)]
        if len(links) > len(best):
            best = links
        if len(best) >= 8:
            break
    return best


def scrape_place(page: Page, code: str, place: Place, *, delay: float) -> RawExcerpt:
    """Save text from the best-ranked sections of a place's code, harvesting the section list first if needed."""
    if not any(section.score >= 0 for section in rank_sections(code, place.name)):
        print(f"  harvest sections for {code}/{place.id}", flush=True)
        links = harvest_toc(page, place.sourceIndex)
        if len(links) < 3:
            raise GapError("no_toc", f"only {len(links)} section links for {place.name}")
        write_toc_csv(code, place.name, links)
        time.sleep(delay)
    sections = [section for section in rank_sections(code, place.name) if section.score >= 0][:3]
    if not sections:
        raise GapError("no_rank", f"no civic section listed for {place.name}")
    last_error = GapError("no_body", f"no usable text for {place.name}")
    for section in sections:
        try:
            text = fetch_text(page, section.url)
        except GapError as exc:
            last_error = exc
        else:
            if excerpt.is_usable(text):
                raw = RawExcerpt(
                    state=code,
                    placeId=place.id,
                    placeName=place.name,
                    url=section.url,
                    title=section.title,
                    text=excerpt.cap(text, excerpt.SCRAPED_CHARS),
                )
                save_raw(raw)
                time.sleep(delay)
                return raw
            last_error = GapError("thin", f"only {len(text)} characters on {section.url}")
        time.sleep(delay)
    raise last_error


def scrape(codes: list[str], *, place_id: str | None, limit: int | None, force: bool, delay: float) -> int:
    failures = Failures(FAILURES_PATH, max_tries=MAX_TRIES)
    done = 0
    blocks = 0
    with browser_page() as page:
        for code in codes:
            state = load_state_file(code)
            if state is None:
                raise SystemExit(f"No data for {code}. Run: python -m pipeline catalog --state {code}")
            for place in state.places:
                if limit is not None and done >= limit:
                    return done
                key = f"{code}/{place.id}"
                if place_id and place.id != place_id:
                    continue
                existing = load_raw(code, place.id)
                if not force and ((existing and excerpt.is_usable(existing.text)) or failures.exhausted(key)):
                    continue
                try:
                    raw = scrape_place(page, code, place, delay=delay)
                except BlockedError as exc:
                    blocks += 1
                    print(f"blocked {key}: {exc}", flush=True)
                    if blocks >= BLOCK_LIMIT:
                        raise SystemExit(f"Stopped after {blocks} blocked requests in a row. Try again later.") from exc
                    time.sleep(delay)
                    continue
                except GapError as exc:
                    tries = failures.record(key, exc.reason, exc)
                    print(f"skip {key} [{exc.reason}, try {tries}]: {exc}", flush=True)
                except PlaywrightError as exc:
                    print(f"skip {key} [browser error]: {exc}", flush=True)
                else:
                    failures.clear(key)
                    done += 1
                    print(f"scraped {key}: {len(raw.text)} characters from {raw.title!r}", flush=True)
                blocks = 0
    return done


def excerpt_counts() -> tuple[int, int, int]:
    """Count saved excerpts that are usable, those too thin to use, and places skipped after repeated failures."""
    usable = thin = 0
    for path in RAW.glob("*/*.json"):
        if excerpt.is_usable(RawExcerpt.model_validate_json(path.read_text(encoding="utf-8")).text):
            usable += 1
        else:
            thin += 1
    return usable, thin, Failures(FAILURES_PATH, max_tries=MAX_TRIES).exhausted_count()
