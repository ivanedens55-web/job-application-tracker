// Mirrors the schemas in docs/openapi.yaml.

export const STATUSES = ["Applied", "Interview", "Offer", "Rejected"] as const;
export type ApplicationStatus = (typeof STATUSES)[number];

export type Application = {
  id: number;
  company: string;
  role: string;
  url: string | null;
  status: ApplicationStatus;
  follow_up_date: string | null; // "YYYY-MM-DD"
  notes: string | null;
  follow_up_due: boolean; // computed by the backend
  created_at: string;
  updated_at: string;
};

export type ApplicationInput = {
  company: string;
  role: string;
  url: string | null;
  status: ApplicationStatus;
  follow_up_date: string | null;
  notes: string | null;
};

export type User = { id: number; email: string };
export type Token = { access_token: string; token_type: "bearer"; expires_in: number };
export type FieldError = { field: string; message: string };
