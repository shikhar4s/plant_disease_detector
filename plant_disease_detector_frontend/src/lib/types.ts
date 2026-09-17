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
  crop_name: string;
  condition_name: string;
  confidence: number;
  severity: string;
  created_at: string;
  recommended_treatment: string;
  expected_recovery_time: string;
  prevention_tips: string[];
  top_predictions: { label: string; disease: string; confidence: number }[];
  guidance_source: string;
  prediction_status: PredictionStatus;
  status: PredictionStatus;
  model_version: string;
  information: {
    crop: string; disease: string; display_name: string; symptoms: string[]; causes: string[];
    actions: string[]; prevention: string[]; disclaimer: string;
  };
  notes: string;
}

export interface HistoryPage {
  count: number;
  next: string | null;
  previous: string | null;
  results: Analysis[];
}

export interface MandiRecord {
  state: string; district: string; market: string; commodity: string; variety: string;
  min_price: number | null; max_price: number | null; modal_price: number | null;
  unit: string; price_date: string;
}
export interface MandiResponse {
  results: MandiRecord[]; count: number; page: number; page_size: number; next: boolean; previous: boolean;
  context_id: string; fetched_at: string; cached: boolean;
  source: { name: string; url: string };
  coverage: { provider_total: number; fetched_limit: number; complete: boolean };
  comparison: null | { highest: MandiRecord; record_count: number; scope: string };
}
export interface CommodityImage {
  url: string; source_url: string; title: string; license: string; credit: string;
}
export interface CommodityImagesResponse {
  images: Record<string, CommodityImage | null>;
  source: { name: string; url: string };
}
export interface MandiHistory {
  status: 'available' | 'collecting' | 'unavailable'; message: string;
  points: { date: string; modal_price: number; unit: string }[];
  percentage_change: number | null; scope: string;
}
export interface WeatherData {
  context_id: string; fetched_at: string; cached: boolean;
  source: { name: string; url: string };
  location: { name: string; state: string; country: string; latitude: number; longitude: number; timezone: string };
  current: Record<string, number>;
  current_units: Record<string, string>;
  forecast: Array<Record<string, number | string>>;
  daily_units: Record<string, string>;
}
export interface RiskData { level: 'Low' | 'Moderate' | 'High' | 'Unavailable'; level_label?: string; score: number | null; reasons: string[]; method: string; rules_version?: string; references?: { title: string; url: string }[] }

