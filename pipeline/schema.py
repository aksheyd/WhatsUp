from __future__ import annotations

import re

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class QuizQuestion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    prompt: str = Field(min_length=8, validation_alias=AliasChoices("prompt", "question"))
    choices: list[str] = Field(min_length=2, max_length=4)
    answer: str

    @model_validator(mode="after")
    def answer_is_a_choice(self) -> QuizQuestion:
        if self.answer not in self.choices:
            raise ValueError(f"answer {self.answer!r} is not one of the choices")
        return self


class QuizBatch(BaseModel):
    questions: list[QuizQuestion] = Field(min_length=3, max_length=5)


class PublishedQuestion(BaseModel):
    id: str
    prompt: str
    choices: list[str]
    answer: str
    excerpt: str
    sourceUrl: str


class Place(BaseModel):
    id: str
    name: str
    sourceIndex: str
    questions: list[PublishedQuestion] = Field(default_factory=list)


class StateFile(BaseModel):
    state: str
    stateName: str
    places: list[Place]


class RawExcerpt(BaseModel):
    state: str
    placeId: str
    placeName: str
    url: str
    title: str = ""
    text: str


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "place"


def question_id(state: str, place_id: str, index: int) -> str:
    return f"{state}:{place_id}:{index}"
