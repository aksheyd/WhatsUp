from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from .schema import QuizBatch

XAI_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4.6"
PROMPT_CACHE_KEY = "whatsup-quiz-v1"
MAX_ATTEMPTS = 3

SYSTEM_PROMPT = """You write short civic quizzes from local US ordinance text.

Rules:
- Use only facts present in the ordinance excerpt. Do not invent penalties, dates, or agencies.
- Write for a regular resident, not a lawyer. Use everyday words.
- Each question has 2 to 4 answer choices. One choice is correct.
- The "answer" field must be copied exactly from one of the "choices".
- Prefer concrete, slightly surprising local rules the excerpt supports: animals, parking, noise, yards, snow, signs.
- Return 3 to 5 questions.
- Each item uses the keys prompt, choices, and answer.

Reply with only a JSON object of the form {"questions": [...]}, with no markdown fences and no commentary."""


class QuizGenerateError(RuntimeError):
    """The model never returned a valid quiz."""

    def __init__(self, message: str, *, output_text: str) -> None:
        super().__init__(message)
        self.output_text = output_text


@dataclass(frozen=True)
class QuizResult:
    quiz: QuizBatch
    output_text: str
    response_id: str
    usage: dict[str, Any] | None
    attempts: int
    latency_ms: int


def make_client(api_key: str) -> OpenAI:
    return OpenAI(base_url=XAI_URL, api_key=api_key, timeout=180.0, max_retries=3)


def parse_quiz(text: str) -> QuizBatch:
    """Read the quiz JSON out of a reply, ignoring markdown fences or text around it."""
    starts = [index for index in (text.find("{"), text.find("[")) if index >= 0]
    if not starts:
        raise ValueError("reply has no JSON")
    value, _ = json.JSONDecoder().raw_decode(text[min(starts) :])
    return QuizBatch.model_validate({"questions": value} if isinstance(value, list) else value)


def generate_quiz(client: OpenAI, *, model: str, prompt: str, temperature: float) -> QuizResult:
    started = time.perf_counter()
    output_text = ""
    last_error: ValueError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = client.responses.create(
            model=model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
            temperature=temperature,
            store=False,
            prompt_cache_key=PROMPT_CACHE_KEY,
        )
        output_text = response.output_text
        try:
            quiz = parse_quiz(output_text)
        except ValueError as exc:
            last_error = exc
            continue
        return QuizResult(
            quiz=quiz,
            output_text=output_text,
            response_id=response.id,
            usage=response.usage.model_dump() if response.usage else None,
            attempts=attempt,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )
    raise QuizGenerateError(f"no valid quiz after {MAX_ATTEMPTS} tries: {last_error}", output_text=output_text)
