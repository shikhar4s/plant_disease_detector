export interface User {
  id: number;
  email: string;
  name: string;
  full_name: string;
  date_joined: string;
  photo_url: string;
  total_uploads: number;
  total_analyzed: number;
  saved_analyses: number;
}

export type PredictionStatus = 'healthy' | 'uncertain' | 'possible_disease';
export interface Analysis {
  id: number;
  image_url: string | null;
  disease: string;
  disease_name: string;
  confidence: number;
  severity: string;
  created_at: string;
  recommended_treatment: string;
  expected_recovery_time: string;
  prevention_tips: string[];
  top_predictions: { label: string; disease: string; confidence: number }[];
  guidance_source: string;
  prediction_status: PredictionStatus;
  notes: string;
}

export interface HistoryPage {
  count: number;
  next: string | null;
  previous: string | null;
  results: Analysis[];
}
