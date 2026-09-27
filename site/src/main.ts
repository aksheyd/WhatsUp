import "./style.css";
import type { CatalogIndex, Place, PlaceSummary, StateList, StateSummary } from "./data";

type Route =
  | { view: "home"; q: string }
  | { view: "places"; state: string; q: string }
  | { view: "quiz"; state: string; place: string; index: number };

type QuizView = { data: StateList; place: Place; index: number };

class LoadError extends Error {}

const SITE = "What's Up?";
const HOME_TITLE = "What's Up? Local law quizzes for US cities and counties";
const PLAYED_KEY = "whatsup-done";
// Must match the breakpoint where style.css switches the state list to the tile map.
const MAP_LAYOUT = "(min-width: 760px)";

// [row, column] of each state on the 11 by 8 tile map shown from tablet width up.
const TILES: Record<string, [number, number]> = {
  AK: [0, 0], ME: [0, 10],
  VT: [1, 9], NH: [1, 10],
  WA: [2, 0], ID: [2, 1], MT: [2, 2], ND: [2, 3], MN: [2, 4], IL: [2, 5], WI: [2, 6], MI: [2, 7], NY: [2, 8], RI: [2, 9], MA: [2, 10],
  OR: [3, 0], NV: [3, 1], WY: [3, 2], SD: [3, 3], IA: [3, 4], IN: [3, 5], OH: [3, 6], PA: [3, 7], NJ: [3, 8], CT: [3, 9],
  CA: [4, 0], UT: [4, 1], CO: [4, 2], NE: [4, 3], MO: [4, 4], KY: [4, 5], WV: [4, 6], VA: [4, 7], MD: [4, 8], DE: [4, 9],
  AZ: [5, 1], NM: [5, 2], KS: [5, 3], AR: [5, 4], TN: [5, 5], NC: [5, 6], SC: [5, 7],
  OK: [6, 3], LA: [6, 4], MS: [6, 5], AL: [6, 6], GA: [6, 7],
  HI: [7, 0], TX: [7, 3], FL: [7, 8],
};

const ICONS = {
  check: `<svg class="icon i-check" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>`,
  cross: `<svg class="icon i-cross" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17"/></svg>`,
  search: `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4 4"/></svg>`,
  chevron: `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>`,
};

const POSITIONAL_CHOICE = /\b(?:all|none|both|neither) of (?:the )?(?:above|these)\b/i;
const MATCH = { exact: 5, prefix: 4, word: 3, inside: 2, typo: 1 } as const;

const app = element<HTMLDivElement>("#app");
const dataCache = new Map<string, Promise<unknown>>();
const scores = new Map<string, Map<number, boolean>>();
let quizUnbind: (() => void) | undefined;
let paintId = 0;

function element<T extends Element>(selector: string, root: ParentNode = document): T {
  const found = root.querySelector<T>(selector);
  if (!found) throw new Error(`Missing ${selector}`);
  return found;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

function plural(n: number, word: string): string {
  return `${fmt(n)} ${word}${n === 1 ? "" : "s"}`;
}

function randomPick<T>(items: T[]): T | undefined {
  return items[Math.floor(Math.random() * items.length)];
}

function placeHref(state: string, place: string, question?: number): string {
  return `#/s/${state}/p/${place}${question === undefined ? "" : `/q/${question}`}`;
}

function searchQuery(value: string): string {
  return value ? `?${new URLSearchParams({ q: value })}` : "";
}

/** Fetch one of the JSON files that vite.config.ts writes at build time. */
function fetchData<T>(path: string, failure: string): Promise<T> {
  let request = dataCache.get(path);
  if (!request) {
    request = fetch(`${import.meta.env.BASE_URL}data/${path}`).then((response) => {
      if (!response.ok) throw new LoadError(failure);
      return response.json();
    });
    request.catch(() => dataCache.delete(path));
    dataCache.set(path, request);
  }
  // The build writes these files from the types in data.ts.
  return request as Promise<T>;
}

function loadIndex(): Promise<CatalogIndex> {
  return fetchData<CatalogIndex>("index.json", "Could not load the list of states.");
}

function loadState(code: string): Promise<StateList> {
  return fetchData<StateList>(`${code}.json`, `There is no state with the code "${code.toUpperCase()}".`);
}

function loadPlace({ state, id }: { state: string; id: string }): Promise<Place> {
  return fetchData<Place>(`places/${state}/${encodeURIComponent(id)}.json`, `Could not load the quiz for ${id}.`);
}

function parseHash(): Route {
  const [path = "", query = ""] = location.hash.replace(/^#/, "").split("?");
  const q = new URLSearchParams(query).get("q") ?? "";
  const [section, state, placeTag, place, questionTag, question] = path.split("/").filter(Boolean);
  if (section !== "s" || !state) return { view: "home", q };
  if (placeTag !== "p" || !place) return { view: "places", state: state.toLowerCase(), q };
  const index = questionTag === "q" ? Number(question) : 0;
  return {
    view: "quiz",
    state: state.toLowerCase(),
    place,
    index: Number.isInteger(index) && index >= 0 ? index : 0,
  };
}

function readPlayed(): Set<string> {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(PLAYED_KEY) ?? "[]");
    return new Set(Array.isArray(stored) ? stored.filter((id): id is string => typeof id === "string") : []);
  } catch {
    // Blocked storage or a corrupt value both mean nothing has been played yet.
    return new Set();
  }
}

function markPlayed(id: string): void {
  const played = readPlayed();
  played.add(id);
  try {
    localStorage.setItem(PLAYED_KEY, JSON.stringify([...played]));
  } catch {
    // Storage can be full or blocked in private browsing, and the Played label is optional.
  }
}

function quizKey({ data, place }: QuizView): string {
  return `${data.state}/${place.id}`;
}

function answers(view: QuizView): Map<number, boolean> {
  const key = quizKey(view);
  let answered = scores.get(key);
  if (!answered) {
    answered = new Map();
    scores.set(key, answered);
  }
  return answered;
}

function shuffleChoices(choices: string[]): string[] {
  const rest = choices.filter((choice) => !POSITIONAL_CHOICE.test(choice));
  const last = choices.filter((choice) => POSITIONAL_CHOICE.test(choice));
  for (let i = rest.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [rest[i], rest[j]] = [rest[j], rest[i]];
  }
  return [...rest, ...last];
}

function header(back?: Pick<StateList, "state" | "stateName">): string {
  return `<header class="top">
    <a class="brand" href="#/"><span class="brand-sign">What's Up?</span></a>
    ${back ? `<nav class="crumbs" aria-label="Breadcrumb"><a href="#/s/${back.state}">${escapeHtml(back.stateName)}</a></nav>` : ""}
  </header>`;
}

function skeleton(view: Route["view"]): string {
  switch (view) {
    case "home":
      return `<main class="page-home" aria-busy="true">
        <div class="hero">
          <div class="hero-main">
            <div class="skel skel-hero-title"></div>
            <div class="skel skel-hero-line"></div>
          </div>
        </div>
      </main>`;
    case "quiz":
      return `${header()}
      <main class="split" aria-busy="true">
        <div class="split-side">
          <div class="skel skel-line"></div>
          <div class="skel skel-title"></div>
        </div>
        <div class="split-main choices">
          <div class="skel skel-choice"></div>
          <div class="skel skel-choice"></div>
          <div class="skel skel-choice"></div>
          <div class="skel skel-choice"></div>
        </div>
      </main>`;
    case "places":
      return `${header()}
      <main aria-busy="true">
        <div class="page-head">
          <div class="skel skel-title"></div>
          <div class="skel skel-line"></div>
        </div>
        <div class="skel skel-bar"></div>
      </main>`;
    default: {
      const unreachable: never = view;
      return unreachable;
    }
  }
}

function statePicker(index: CatalogIndex): string {
  const states = [...index.states].sort((a, b) => a.name.localeCompare(b.name));
  return `<ul class="state-map" id="results">
    ${states
      .map((state) => {
        const [row, col] = TILES[state.code] ?? [0, 0];
        return `<li style="--row:${row + 1};--col:${col + 1}" data-code="${state.code}">
          <a class="state-tile" href="#/s/${state.code.toLowerCase()}" title="${escapeHtml(state.name)}">
            <span class="state-code" aria-hidden="true">${escapeHtml(state.code)}</span>
            <span class="state-name">${escapeHtml(state.name)}</span>
            <span class="state-count">${fmt(state.questionCount)}<span class="state-unit"> ${state.questionCount === 1 ? "question" : "questions"}</span></span>
          </a>
        </li>`;
      })
      .join("")}
  </ul>`;
}

function renderHome(index: CatalogIndex, q: string): string {
  const questions = index.states.reduce((sum, state) => sum + state.questionCount, 0);
  const places = index.states.reduce((sum, state) => sum + state.placeCount, 0);
  return `<main class="page-home">
      <section class="hero">
        <div class="hero-main">
          <h1>What's up?</h1>
          <p class="hero-lede"><span>Grok wrote quizzes on the local laws of thousands of US cities and counties.</span> <span>Do you know what's up in your county?</span></p>
          <div class="actions">
            <button class="btn btn-light" id="surprise" type="button">Surprise me</button>
            <button class="btn btn-ghost" id="find-state" type="button">Search states</button>
          </div>
        </div>
        <ul class="facts">
          <li><strong>${fmt(questions)}</strong><span>questions</span></li>
          <li><strong>${fmt(places)}</strong><span>cities and counties</span></li>
          <li><strong>${fmt(index.states.length)}</strong><span>states</span></li>
        </ul>
      </section>
      <section class="section" aria-labelledby="pick">
        <div class="section-head">
          <h2 id="pick">Pick a state</h2>
          <p class="legend">The number on each state is its question count.</p>
        </div>
        <div class="toolbar" id="state-search">
          <label class="search">
            ${ICONS.search}
            <input id="filter" type="search" value="${escapeHtml(q)}" placeholder="Search states" aria-label="Search states" autocomplete="off" />
          </label>
        </div>
        ${statePicker(index)}
        <p class="empty" id="none" hidden>No state matches that search.</p>
      </section>
    </main>
    <footer class="foot">
      <div class="foot-block foot-about">
        <h2>About</h2>
        <p>Started at the University of Michigan Data Driven Hackathon in March 2025. Revived in September 2026 with new quizzes.</p>
      </div>
      <div class="foot-block">
        <h2>Sources</h2>
        <p>Questions quote short excerpts from <a href="https://library.municode.com" target="_blank" rel="noreferrer">Municode</a>. A few links may be off.</p>
      </div>
      <div class="foot-block">
        <h2>Code</h2>
        <p><a href="https://github.com/aksheyd/whatsup" target="_blank" rel="noreferrer">Source on GitHub</a></p>
      </div>
      <div class="foot-bar">
        <p class="foot-name">What's Up?</p>
        <p>Unofficial. Not affiliated with any city, county, or Municode.</p>
      </div>
    </footer>`;
}

function renderPlaces(data: StateList, q: string): string {
  const played = readPlayed();
  const ready = data.places.filter((place) => place.questionCount > 0).length;
  return `${header()}
    <main>
      <div class="page-head">
        <h1>${escapeHtml(data.stateName)}</h1>
        <p class="sub">${fmt(ready)} of ${fmt(data.places.length)} places have a quiz.</p>
      </div>
      <div class="toolbar">
        <label class="search">
          ${ICONS.search}
          <input id="filter" type="search" value="${escapeHtml(q)}" placeholder="Search cities and counties" aria-label="Search places in ${escapeHtml(data.stateName)}" autocomplete="off" />
        </label>
        <label class="check"><input type="checkbox" id="ready-only" checked /> Only places with a quiz</label>
      </div>
      <ul class="place-grid" id="results">
        ${data.places
          .map((place) => {
            const has = place.questionCount > 0;
            const meta = !has
              ? `<span class="place-meta">No quiz yet</span>`
              : played.has(`${data.state}/${place.id}`)
                ? `<span class="place-meta is-done">${ICONS.check}Played</span>`
                : `<span class="place-meta">${plural(place.questionCount, "question")}</span>`;
            return `<li data-filter="${escapeHtml(place.name.toLowerCase())}" data-ready="${has ? "1" : "0"}">
              <a class="place${has ? "" : " is-empty"}" href="${placeHref(data.state, place.id)}">
                <span class="place-name">${escapeHtml(place.name)}</span>
                ${meta}
              </a>
            </li>`;
          })
          .join("")}
      </ul>
      <p class="empty" id="none" hidden>No place matches that search. Places without a quiz are hidden while "Only places with a quiz" is on.</p>
    </main>`;
}

function renderNoQuiz(data: StateList, place: PlaceSummary): string {
  return `${header(data)}
    <main class="split">
      <div class="split-side">
        <p class="context">${escapeHtml(data.stateName)}</p>
        <h1 class="split-title">${escapeHtml(place.name)}</h1>
      </div>
      <div class="split-main">
        <p class="lead">There is no quiz for ${escapeHtml(place.name)} yet.</p>
        <p class="sub">You can still read its ordinances on Municode.</p>
        <div class="actions">
          <a class="btn btn-primary" href="${escapeHtml(place.sourceIndex)}" target="_blank" rel="noreferrer">Open the code on Municode</a>
          <a class="btn btn-secondary" href="#/s/${data.state}">Back to ${escapeHtml(data.stateName)}</a>
        </div>
      </div>
    </main>`;
}

function renderResults(view: QuizView): string {
  const { data, place } = view;
  const total = place.questions.length;
  const correct = [...answers(view).values()].filter(Boolean).length;
  return `${header(data)}
    <main class="split">
      <div class="split-side">
        <p class="context">${escapeHtml(place.name)}, ${escapeHtml(data.stateName)}</p>
        <h1 class="split-title">You got ${correct} of ${total} right.</h1>
      </div>
      <div class="split-main">
        <p class="lead">${
          correct === total
            ? "Try another place, or play this one again."
            : "Play again to see the rules you missed, or try another place."
        }</p>
        <div class="actions">
          <a class="btn btn-primary" href="${placeHref(data.state, place.id, 0)}">Play again</a>
          <button class="btn btn-secondary" id="another" type="button">Another place in ${escapeHtml(data.stateName)}</button>
        </div>
      </div>
    </main>`;
}

function renderQuestion(view: QuizView): string {
  const { data, place, index } = view;
  const total = place.questions.length;
  const question = place.questions[index];
  const choices = shuffleChoices(question.choices);
  const keys = choices.length > 2 ? `1 to ${choices.length}` : "1 or 2";
  const segments = Array.from({ length: total }, (_, i) => `<i${i <= index ? ` class="on"` : ""}></i>`).join("");
  return `${header(data)}
    <main class="split" data-quiz>
      <div class="split-side">
        <p class="context">${escapeHtml(place.name)}, ${escapeHtml(data.stateName)}</p>
        <div class="progress">
          <span class="progress-label">Question ${index + 1} of ${total}</span>
          <span class="progress-bar" aria-hidden="true">${segments}</span>
        </div>
        <h1 class="prompt">${escapeHtml(question.prompt)}</h1>
        <p class="hint">Press ${keys} to answer and Enter to continue.</p>
      </div>
      <div class="split-main">
        <div class="choices">
          ${choices
            .map(
              (choice, i) =>
                `<button class="choice" type="button" data-choice="${escapeHtml(choice)}" data-key="${i + 1}">
                  <span class="key" aria-hidden="true">${i + 1}</span>
                  <span>${escapeHtml(choice)}<span class="sr-only choice-status"></span></span>
                  <span class="mark" aria-hidden="true">${ICONS.check}${ICONS.cross}</span>
                </button>`,
            )
            .join("")}
        </div>
        <div class="reveal" id="reveal" hidden>
          <p class="verdict" id="verdict" role="status"></p>
          <div class="reveal-actions">
            <a class="btn btn-primary" id="next" href="${placeHref(data.state, place.id, index + 1)}">${index + 1 < total ? "Next question" : "See your score"}</a>
            <a class="source-link" href="${escapeHtml(question.sourceUrl)}" target="_blank" rel="noreferrer">Read the full ordinance on Municode</a>
          </div>
          ${
            question.excerpt
              ? `<details class="excerpt">
            <summary>${ICONS.chevron}Ordinance excerpt</summary>
            <div class="excerpt-body">${escapeHtml(question.excerpt)}</div>
          </details>`
              : ""
          }
        </div>
      </div>
    </main>`;
}

function renderMissingPlace(data: StateList): string {
  return `${header(data)}
    <main>
      <div class="page-head">
        <h1>Place not found</h1>
        <p class="sub">No place in ${escapeHtml(data.stateName)} matches this link.</p>
      </div>
      <a class="btn btn-secondary" href="#/s/${data.state}">Back to ${escapeHtml(data.stateName)}</a>
    </main>`;
}

function renderError(error: unknown): string {
  const message = error instanceof LoadError ? error.message : "Check your connection, then reload the page.";
  return `${header()}
    <main>
      <div class="page-head">
        <h1>Could not load this page</h1>
        <p class="sub">${escapeHtml(message)}</p>
      </div>
      <a class="btn btn-secondary" href="#/">Go to the home page</a>
    </main>`;
}

function bindPlaceFilter(state: string): void {
  const input = element<HTMLInputElement>("#filter");
  const readyOnly = element<HTMLInputElement>("#ready-only");
  const none = element<HTMLElement>("#none");
  const items = [...document.querySelectorAll<HTMLElement>("[data-filter]")];
  const apply = () => {
    const term = input.value.trim().toLowerCase();
    for (const item of items) {
      item.hidden = !(item.dataset.filter ?? "").includes(term) || (readyOnly.checked && item.dataset.ready === "0");
    }
    none.hidden = items.some((item) => !item.hidden);
    history.replaceState(null, "", `#/s/${state}${searchQuery(input.value)}`);
  };
  input.addEventListener("input", apply);
  readyOnly.addEventListener("change", apply);
  apply();
}

function centerMap(): void {
  const map = element<HTMLElement>("#results");
  const bar = element<HTMLElement>("#state-search");
  const mapTop = map.getBoundingClientRect().top + window.scrollY;
  const barTop = mapTop - parseFloat(getComputedStyle(bar).marginBottom) - bar.offsetHeight;
  const centered = mapTop + map.offsetHeight / 2 - window.innerHeight / 2;
  const top = window.matchMedia(MAP_LAYOUT).matches ? Math.min(centered, barTop) : barTop;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  window.scrollTo({ top, behavior: reduce ? "auto" : "smooth" });
}

function editDistance(a: string, b: string): number {
  const d = Array.from({ length: a.length + 1 }, (_, i) =>
    Array.from({ length: b.length + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)),
  );
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
      }
    }
  }
  return d[a.length][b.length];
}

function stateScore(term: string, state: StateSummary): number {
  const name = state.name.toLowerCase();
  if (term === state.code.toLowerCase() || term === name) return MATCH.exact;
  if (name.startsWith(term)) return MATCH.prefix;
  const words = name.split(" ");
  if (words.some((word) => word.startsWith(term))) return MATCH.word;
  if (name.includes(term)) return MATCH.inside;
  if (term.length < 4) return 0;
  const limit = term.length < 6 ? 1 : 2;
  const lengths = [term.length - 1, term.length, term.length + 1];
  const close = [name, ...words].some((text) =>
    lengths.some((length) => editDistance(term, text.slice(0, length)) <= limit),
  );
  return close ? MATCH.typo : 0;
}

function bindStateSearch(index: CatalogIndex): void {
  const input = element<HTMLInputElement>("#filter");
  const map = element<HTMLElement>("#results");
  const none = element<HTMLElement>("#none");
  const byCode = new Map(index.states.map((state) => [state.code, state]));
  const items = [...map.querySelectorAll<HTMLElement>("li[data-code]")].flatMap((item) => {
    const state = byCode.get(item.dataset.code ?? "");
    return state ? [{ item, state }] : [];
  });
  const apply = () => {
    const term = input.value.trim().toLowerCase().replace(/\s+/g, " ");
    const scored = items.map((entry) => ({ ...entry, score: term ? stateScore(term, entry.state) : 0 }));
    const literal = scored.some((entry) => entry.score > MATCH.typo);
    const ranked = scored
      .map((entry) => (literal && entry.score === MATCH.typo ? { ...entry, score: 0 } : entry))
      .sort((a, b) => b.score - a.score || a.state.name.localeCompare(b.state.name));
    const best = ranked[0]?.score ?? 0;
    for (const { item, score } of ranked) {
      const out = Boolean(term) && score === 0;
      item.classList.toggle("is-out", out);
      item.inert = out;
      if (score > 0) item.dataset.rank = String(score === best ? 3 : score >= MATCH.word ? 2 : 1);
      else delete item.dataset.rank;
    }
    const order = ranked.map((entry) => entry.item);
    if (order.some((item, i) => map.children[i] !== item)) map.append(...order);
    none.hidden = !term || best > 0;
    history.replaceState(null, "", `#/${searchQuery(input.value)}`);
  };
  element<HTMLButtonElement>("#find-state").addEventListener("click", () => {
    centerMap();
    input.focus({ preventScroll: true });
  });
  input.addEventListener("input", () => {
    apply();
    centerMap();
  });
  apply();
}

function randomPlace(data: StateList, skip?: string): PlaceSummary | undefined {
  const withQuiz = data.places.filter((place) => place.questionCount > 0);
  return randomPick(withQuiz.filter((place) => place.id !== skip)) ?? randomPick(withQuiz);
}

async function surprise(index: CatalogIndex): Promise<void> {
  const state = randomPick(index.states.filter((item) => item.questionCount > 0));
  if (!state) return;
  const data = await loadState(state.code.toLowerCase());
  const place = randomPlace(data);
  if (place) location.hash = placeHref(data.state, place.id);
}

function bindSurprise(index: CatalogIndex): void {
  element<HTMLButtonElement>("#surprise").addEventListener("click", () => void surprise(index));
}

function bindAnother(view: QuizView): void {
  element<HTMLButtonElement>("#another").addEventListener("click", () => {
    const place = randomPlace(view.data, view.place.id);
    if (place) location.hash = placeHref(view.data.state, place.id);
  });
}

function bindQuiz(view: QuizView): void {
  const { place, index } = view;
  const root = element<HTMLElement>("[data-quiz]");
  const question = place.questions[index];
  let locked = false;
  const choose = (picked: string) => {
    if (locked) return;
    locked = true;
    const ok = picked === question.answer;
    answers(view).set(index, ok);
    if (index + 1 >= place.questions.length) markPlayed(quizKey(view));
    for (const button of root.querySelectorAll<HTMLButtonElement>(".choice")) {
      button.disabled = true;
      const status = element<HTMLElement>(".choice-status", button);
      if (button.dataset.choice === question.answer) {
        button.classList.add("correct");
        status.textContent = " (correct answer)";
      } else if (button.dataset.choice === picked && !ok) {
        button.classList.add("wrong");
        status.textContent = " (your answer)";
      }
    }
    element<HTMLElement>("#reveal").hidden = false;
    const verdict = element<HTMLElement>("#verdict");
    verdict.classList.add(ok ? "ok" : "no");
    verdict.innerHTML = ok
      ? `${ICONS.check}<span>Correct.</span>`
      : `${ICONS.cross}<span>Not quite. The right answer has a check mark.</span>`;
    element<HTMLAnchorElement>("#next").focus();
  };

  for (const button of root.querySelectorAll<HTMLButtonElement>(".choice")) {
    button.addEventListener("click", () => choose(button.dataset.choice ?? ""));
  }

  const onKey = (event: KeyboardEvent) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === "Enter" && locked) {
      event.preventDefault();
      element<HTMLAnchorElement>("#next").click();
      return;
    }
    const button = Number(event.key) ? root.querySelector<HTMLButtonElement>(`.choice[data-key="${event.key}"]`) : null;
    if (button && !locked) {
      event.preventDefault();
      choose(button.dataset.choice ?? "");
    }
  };
  window.addEventListener("keydown", onKey);
  quizUnbind = () => window.removeEventListener("keydown", onKey);
}

async function paint(): Promise<void> {
  quizUnbind?.();
  quizUnbind = undefined;
  const id = ++paintId;
  const route = parseHash();
  const show = (html: string, title: string): boolean => {
    if (id !== paintId) return false;
    app.innerHTML = html;
    document.title = title;
    return true;
  };
  app.innerHTML = skeleton(route.view);
  window.scrollTo(0, 0);
  try {
    switch (route.view) {
      case "home": {
        const index = await loadIndex();
        if (show(renderHome(index, route.q), HOME_TITLE)) {
          bindSurprise(index);
          bindStateSearch(index);
        }
        return;
      }
      case "places": {
        const data = await loadState(route.state);
        if (show(renderPlaces(data, route.q), `${data.stateName} | ${SITE}`)) bindPlaceFilter(data.state);
        return;
      }
      case "quiz": {
        const data = await loadState(route.state);
        const summary = data.places.find((item) => item.id === route.place);
        if (!summary) {
          show(renderMissingPlace(data), `Place not found | ${SITE}`);
          return;
        }
        const title = `${summary.name}, ${data.stateName} | ${SITE}`;
        if (summary.questionCount === 0) {
          show(renderNoQuiz(data, summary), title);
          return;
        }
        const view: QuizView = { data, place: await loadPlace({ state: data.state, id: summary.id }), index: route.index };
        if (route.index === 0) scores.delete(quizKey(view));
        const finished = route.index >= view.place.questions.length;
        if (!show(finished ? renderResults(view) : renderQuestion(view), title)) return;
        if (finished) bindAnother(view);
        else bindQuiz(view);
        return;
      }
    }
  } catch (error) {
    show(renderError(error), SITE);
  }
}

window.addEventListener("hashchange", () => void paint());
void paint();
