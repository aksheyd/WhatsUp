import type { Question } from "./src/data";

const STOP = new Set(
  (
    "the and for are but not you all any can had has her his its was who how may per via own one two use set get out off now new our too yes " +
    "about above after also among another been before being below between both city code county does each either every except from have having " +
    "here into just least less many more most much must near only other over part people person same section shall should since some such than " +
    "that their them then there these they this those through town under unless until upon used very village were what when where whether which " +
    "while will with within without would your according ordinance rule rules allowed required generally"
  ).split(" "),
);

const BOILERPLATE = /^(?:footnotes:|editor's note|cross reference|state law reference|chapters?:|sections?:|articles?:)/i;

type Passage = { text: string; terms: Set<string> };

const passageCache = new Map<string, Passage[]>();

function stem(word: string): string {
  if (/\d/.test(word)) return word;
  const stemmed = word.replace(/ies$/, "y").replace(/(?:ing|ed|s)$/, "");
  return stemmed.length >= 3 ? stemmed : word;
}

function terms(text: string): Set<string> {
  const found = new Set<string>();
  for (const word of text.toLowerCase().match(/[a-z]{3,}|\d+(?:\.\d+)?/g) ?? []) {
    if (!STOP.has(word)) found.add(stem(word));
  }
  return found;
}

function splitPassages(text: string): string[] {
  const paragraphs = text
    .replace(/[ \t]*\n[ \t]+/g, " ")
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.replace(/\s+/g, " ").trim())
    .filter((paragraph) => paragraph && !BOILERPLATE.test(paragraph));
  const out: string[] = [];
  for (const paragraph of paragraphs) {
    if (paragraph.length <= 700) {
      out.push(paragraph);
      continue;
    }
    let current = "";
    for (const sentence of paragraph.split(/(?<=[.;:])\s+(?=[A-Z(0-9])/)) {
      if (current && current.length + sentence.length > 600) {
        out.push(current);
        current = sentence;
      } else {
        current = current ? `${current} ${sentence}` : sentence;
      }
    }
    if (current) out.push(current);
  }
  return out;
}

function passagesOf(excerpt: string): Passage[] {
  let passages = passageCache.get(excerpt);
  if (!passages) {
    passages = splitPassages(excerpt).map((text) => ({ text, terms: terms(text) }));
    passageCache.set(excerpt, passages);
  }
  return passages;
}

function supports({ answerHits, answerTotal, promptHits }: { answerHits: number; answerTotal: number; promptHits: number }): boolean {
  if (answerTotal >= 3) return answerHits >= 2 && answerHits / answerTotal >= 0.4;
  if (answerTotal > 0) return answerHits === answerTotal && promptHits >= 1;
  return promptHits >= 3;
}

/** The passage of a question's excerpt that best supports its answer, or "" when none does. */
function focusExcerpt(question: Question): string {
  const answerTerms = terms(question.answer);
  const promptTerms = [...terms(question.prompt)].filter((term) => !answerTerms.has(term));
  const parts = passagesOf(question.excerpt);
  let best = -1;
  let bestScore = 0;
  parts.forEach((part, index) => {
    const answerHits = [...answerTerms].filter((term) => part.terms.has(term)).length;
    const promptHits = promptTerms.filter((term) => part.terms.has(term)).length;
    const score = answerHits * 3 + promptHits;
    if (supports({ answerHits, answerTotal: answerTerms.size, promptHits }) && score > bestScore) {
      best = index;
      bestScore = score;
    }
  });
  if (best < 0) return "";
  const next = parts[best + 1];
  return parts[best].text.length < 300 && next ? `${parts[best].text}\n\n${next.text}` : parts[best].text;
}

// Excerpts under 400 characters turned out to be page chrome, like a title page or a "Load more" button.
function hasSourceText(excerpt: string): boolean {
  const text = excerpt.trim();
  return text.length >= 400 && !/^(?:table of contents|load more)/i.test(text);
}

/** Drops questions written without real source text, and trims each remaining excerpt to the passage that supports its answer, leaving it empty when none does. */
export function publishableQuestions(questions: Question[]): Question[] {
  return questions
    .filter((question) => hasSourceText(question.excerpt))
    .map((question) => ({ ...question, excerpt: focusExcerpt(question) }));
}
