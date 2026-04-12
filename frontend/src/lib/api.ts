const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ChangeRequest {
  id: string;
  customer_id: string;
  change_type: string;
  requested_old_value: Record<string, string>;
  requested_new_value: Record<string, string>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  request_id: string;
  document_type: string;
  original_filename: string;
  filenet_reference_id: string | null;
  uploaded_at: string;
}

export interface VerificationResult {
  id: string;
  request_id: string;
  document_id: string;
  extracted_fields: Record<string, unknown>;
  field_scores: Record<string, number>;
  overall_confidence: number;
  forgery_check: string;
  ai_summary: string | null;
  ai_recommendation: string | null;
  verified_at: string;
}

export interface CheckerDecision {
  id: string;
  request_id: string;
  checker_id: string;
  decision: string;
  notes: string | null;
  decided_at: string;
  rps_response: Record<string, unknown> | null;
}

export interface ReviewDetail {
  request: ChangeRequest;
  documents: Document[];
  verification: VerificationResult | null;
  decisions: CheckerDecision[];
}

export interface PendingItem {
  id: string;
  customer_id: string;
  change_type: string;
  requested_new_value: Record<string, string>;
  overall_confidence: number | null;
  ai_recommendation: string | null;
  created_at: string;
}

// ── API Functions ─────────────────────────────────────────────────────────────

export const api = {
  createRequest: (body: {
    customer_id: string;
    change_type: string;
    requested_old_value: Record<string, string>;
    requested_new_value: Record<string, string>;
  }) =>
    apiFetch<ChangeRequest>("/api/v1/requests", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getRequest: (id: string) => apiFetch<ChangeRequest>(`/api/v1/requests/${id}`),

  uploadDocument: (requestId: string, documentType: string, file: File) => {
    const form = new FormData();
    form.append("document_type", documentType);
    form.append("file", file);
    return fetch(`${API_URL}/api/v1/requests/${requestId}/documents`, {
      method: "POST",
      body: form,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return res.json() as Promise<Document>;
    });
  },

  getPending: () => apiFetch<PendingItem[]>("/api/v1/checker/pending"),

  getReviewDetail: (id: string) =>
    apiFetch<ReviewDetail>(`/api/v1/checker/requests/${id}`),

  approve: (id: string, checker_id: string, notes?: string) =>
    apiFetch<CheckerDecision>(`/api/v1/checker/requests/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ checker_id, decision: "APPROVED", notes }),
    }),

  reject: (id: string, checker_id: string, notes?: string) =>
    apiFetch<CheckerDecision>(`/api/v1/checker/requests/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ checker_id, decision: "REJECTED", notes }),
    }),

  health: () => apiFetch<{ status: string }>("/health"),
};
