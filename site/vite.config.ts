import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { defineConfig, type Plugin } from "vite";
import { publishableQuestions } from "./excerpts";
import type { CatalogIndex, PublishedState, StateList, StateSummary } from "./src/data";

const PUBLISHED = join(import.meta.dirname, "../data/published");
const OUT = join(import.meta.dirname, "public/data");

/** Split the committed state files into the index, per-state lists, and per-place quizzes the site loads. */
function splitPublishedData(): void {
  rmSync(OUT, { recursive: true, force: true });
  mkdirSync(OUT, { recursive: true });
  const states: StateSummary[] = [];
  for (const file of readdirSync(PUBLISHED).filter((name) => name.endsWith(".json")).sort()) {
    // The pipeline validates these files against its pydantic models when it writes them.
    const data: PublishedState = JSON.parse(readFileSync(join(PUBLISHED, file), "utf8"));
    const places = data.places.map((place) => ({ ...place, questions: publishableQuestions(place.questions) }));
    const list: StateList = {
      state: data.state,
      stateName: data.stateName,
      places: places.map(({ questions, ...place }) => ({ ...place, questionCount: questions.length })),
    };
    writeFileSync(join(OUT, `${data.state}.json`), JSON.stringify(list));
    const withQuiz = places.filter((place) => place.questions.length > 0);
    for (const place of withQuiz) {
      const dir = join(OUT, "places", data.state);
      mkdirSync(dir, { recursive: true });
      writeFileSync(join(dir, `${place.id}.json`), JSON.stringify(place));
    }
    states.push({
      code: data.state.toUpperCase(),
      name: data.stateName,
      placeCount: withQuiz.length,
      questionCount: withQuiz.reduce((sum, place) => sum + place.questions.length, 0),
    });
  }
  const index: CatalogIndex = { states };
  writeFileSync(join(OUT, "index.json"), JSON.stringify(index));
}

export default defineConfig({
  base: process.env.GITHUB_PAGES === "1" ? "/whatsup/" : "/",
  plugins: [{ name: "split-published-data", buildStart: splitPublishedData } satisfies Plugin],
});
