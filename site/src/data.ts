/** Shapes of the committed files in data/published and of the files vite.config.ts writes to public/data. */

export type Question = {
  id: string;
  prompt: string;
  choices: string[];
  answer: string;
  excerpt: string;
  sourceUrl: string;
};

export type Place = {
  id: string;
  name: string;
  sourceIndex: string;
  questions: Question[];
};

export type PublishedState = {
  state: string;
  stateName: string;
  places: Place[];
};

export type PlaceSummary = Omit<Place, "questions"> & { questionCount: number };

export type StateList = Omit<PublishedState, "places"> & { places: PlaceSummary[] };

export type StateSummary = {
  code: string;
  name: string;
  placeCount: number;
  questionCount: number;
};

export type CatalogIndex = { states: StateSummary[] };
