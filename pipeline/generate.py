from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from openai import OpenAIError

from . import excerpt
from .catalog import load_state_file, save_state_file
from .lm import SYSTEM_PROMPT, QuizGenerateError, QuizResult, generate_quiz, make_client
from .paths import RAW, TRACES
from .schema import Place, PublishedQuestion, RawExcerpt, StateFile, question_id
from .store import Failures, load_raw

FAILURES_PATH = RAW / "generate_status.json"
MAX_TRIES = 2


@dataclass(frozen=True)
class Job:
    state: StateFile
    place: Place
    raw: RawExcerpt

    @property
    def key(self) -> str:
        return f"{self.state.state}/{self.place.id}"


def build_prompt(job: Job) -> str:
    return (
        f"State: {job.state.state.upper()}\n"
        f"Place: {job.place.name}\n"
        f"Source: {job.raw.url}\n\n"
        f"Ordinance excerpt:\n{excerpt.cap(job.raw.text, excerpt.PROMPT_CHARS)}"
    )


def publish(job: Job, result: QuizResult) -> None:
    shown = excerpt.cap(job.raw.text, excerpt.PUBLISHED_CHARS)
    job.place.questions = [
        PublishedQuestion(
            id=question_id(job.state.state, job.place.id, index),
            prompt=question.prompt,
            choices=question.choices,
            answer=question.answer,
            excerpt=shown,
            sourceUrl=job.raw.url,
        )
        for index, question in enumerate(result.quiz.questions)
    ]


def save_trace(job: Job, *, prompt: str, model: str, **details: Any) -> None:
    """Keep each model call in .traces/ so a question can be traced back to its prompt and reply."""
    TRACES.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    trace = {"place": job.key, "model": model, "instructions": SYSTEM_PROMPT, "input": prompt, **details}
    path = TRACES / f"{stamp}_{job.state.state}_{job.place.id}.json"
    path.write_text(json.dumps(trace, indent=2, default=str) + "\n", encoding="utf-8")


def plan_jobs(
    codes: list[str], *, place_id: str | None, limit: int | None, force: bool, failures: Failures
) -> list[Job]:
    jobs: list[Job] = []
    for code in codes:
        state = load_state_file(code)
        if state is None:
            continue
        for place in state.places:
            if place_id and place.id != place_id:
                continue
            if not force and (place.questions or failures.exhausted(f"{code}/{place.id}")):
                continue
            raw = load_raw(code, place.id)
            if raw and excerpt.is_usable(raw.text):
                jobs.append(Job(state=state, place=place, raw=raw))
    return jobs[:limit]


def generate(
    codes: list[str],
    *,
    api_key: str,
    model: str,
    temperature: float,
    concurrency: int,
    place_id: str | None = None,
    limit: int | None = None,
    force: bool = False,
) -> int:
    failures = Failures(FAILURES_PATH, max_tries=MAX_TRIES)
    jobs = plan_jobs(codes, place_id=place_id, limit=limit, force=force, failures=failures)
    print(f"{len(jobs)} places to generate with {model}, {concurrency} at a time", flush=True)
    if not jobs:
        return 0
    client = make_client(api_key)
    save_lock = threading.Lock()
    done = 0

    def run(job: Job) -> None:
        nonlocal done
        prompt = build_prompt(job)
        try:
            result = generate_quiz(client, model=model, prompt=prompt, temperature=temperature)
        except (QuizGenerateError, OpenAIError) as exc:
            output_text = exc.output_text if isinstance(exc, QuizGenerateError) else ""
            save_trace(job, prompt=prompt, model=model, error=str(exc), output_text=output_text)
            tries = failures.record(job.key, type(exc).__name__, exc)
            print(f"fail {job.key} [try {tries}]: {exc}", flush=True)
            return
        save_trace(
            job,
            prompt=prompt,
            model=model,
            output_text=result.output_text,
            response_id=result.response_id,
            usage=result.usage,
            attempts=result.attempts,
            latency_ms=result.latency_ms,
        )
        with save_lock:
            publish(job, result)
            save_state_file(job.state)
            failures.clear(job.key)
            done += 1
            print(f"generated {job.key}: {len(job.place.questions)} questions ({done}/{len(jobs)})", flush=True)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(run, jobs))
    return done
