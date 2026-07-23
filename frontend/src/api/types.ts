export interface SourceInfo {
  id: string;
  display_name: string;
  available: boolean;
  missing: string[];
}

export interface Campaign {
  id: number;
  name: string;
  niche: string;
  city: string;
  source: string;
  status: "draft" | "collecting" | "ready" | "failed";
  created_at: string;
  lead_counts: Record<string, number>;
}

export interface Lead {
  id: number;
  campaign_id: number;
  external_id: string | null;
  name: string;
  category: string | null;
  address: string | null;
  phone_e164: string | null;
  website: string | null;
  website_status: "none" | "dead" | "alive" | "unknown";
  whatsapp_url: string | null;
  telegram_url: string | null;
  instagram_url: string | null;
  rating: number | null;
  reviews_count: number | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface LeadPage {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
}

export interface Message {
  id: number;
  lead_id: number;
  text: string;
  provider: string;
  model: string;
  created_at: string;
}

export interface Job {
  id: string;
  kind: string;
  campaign_id: number | null;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  progress: number;
  detail: string | null;
  created_at: string;
  finished_at: string | null;
}
