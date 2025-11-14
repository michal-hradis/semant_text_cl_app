// API Type Definitions based on Pydantic models

export interface TitleImport {
  id: string;
  generated_title: string;
  model: string;
  query: string;
  prompt: string;
}

export interface ChunkImport {
  id: string;
  text: string;
  start_page_id: string;
  from_page: number;
  to_page: number;
  order: number;
  language: string;
  vector_index: number;
  document: string;
  generated_titles: TitleImport[];
}

export interface RatedTitle extends TitleImport {
  preferred: boolean;
  is_irrelevant: boolean;
  is_gibberish: boolean;
  is_relevant: boolean;
  is_hallucination: boolean;
  is_long: boolean;
}

export interface SingleRating {
  titles: RatedTitle[];
  start_time: string; // ISO datetime string
  end_time: string; // ISO datetime string
}

export interface RatingResponseNew {
  id: string;
  request_id: string;
  start_time: string; // ISO datetime string
  end_time: string; // ISO datetime string
  ratings: SingleRating[];
}

export interface RatingRequestNew {
  id: string;
  chunk: ChunkImport;
  titles_lists: TitleImport[][];
  ratings_requested: number;
  ratings_done: number;
  ratings_to_go: number;
}

export interface RatingRequest extends RatingRequestNew {
  created_at: string; // ISO datetime string
}

export interface UserRead {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface UserCreate {
  email: string;
  password: string;
  is_active?: boolean;
  is_superuser?: boolean;
  is_verified?: boolean;
}

export interface BearerResponse {
  access_token: string;
  token_type: string;
}
