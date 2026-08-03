export interface UserOut {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
}

export interface WorkspaceOut {
  id: string;
  name: string;
  slug: string;
}

export interface CurrentUser {
  user: UserOut;
  workspaces: WorkspaceOut[];
  active_workspace_id: string | null;
}

export interface RecordOut {
  id: string;
  record_type: string | null;
  title: string | null;
  description: string | null;
  jurisdiction: string | null;
  filing_date: string | null;
  case_number: string | null;
  original_url: string | null;
  primary_name: string | null;
  normalized_name: string | null;
  normalized_address: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  is_demo: boolean;
  created_at: string;
}

export interface EntityMention {
  id: string;
  entity_type: string;
  value: string;
  normalized_value: string | null;
  extraction_method: string;
  confidence: number;
  page_number: number | null;
  char_start: number | null;
  char_end: number | null;
  source_text: string | null;
}

export interface RecordDetail extends RecordOut {
  raw_payload: Record<string, unknown> | null;
  normalized_payload: Record<string, unknown> | null;
  entities: EntityMention[];
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface MatchCandidate {
  id: string;
  record_a_id: string;
  record_b_id: string;
  confidence_score: number;
  category: string;
  feature_scores: Record<string, number> | null;
  supporting_evidence: Array<Record<string, unknown>> | null;
  conflicting_evidence: Array<Record<string, unknown>> | null;
  missing_information: string[] | null;
  rationale: string | null;
  rationale_source: string;
  review_status: string;
  created_at: string;
  record_a?: RecordOut | null;
  record_b?: RecordOut | null;
}

export interface AdapterDescriptor {
  source_key: string;
  source_name: string;
  source_type: string;
  access_method: string;
  jurisdiction: string | null;
  supported_record_types: string[];
  terms_notes: string;
  attribution: string;
  requires_auth: boolean;
  rate_limit_per_minute: number | null;
}

export interface DashboardMetrics {
  total_records: number;
  total_documents: number;
  records_this_week: number;
  documents_pending: number;
  matches_pending_review: number;
  matches_reviewed: number;
  failed_jobs: number;
  recent_activity: Array<{
    action: string;
    result_count: number | null;
    created_at: string;
    query: Record<string, unknown> | null;
  }>;
}

export interface ProjectOut {
  id: string;
  name: string;
  objective: string | null;
  created_at: string;
  records?: RecordOut[];
}

export interface SavedSearchOut {
  id: string;
  name: string;
  query: Record<string, unknown>;
  last_executed_at: string | null;
  last_result_count: number | null;
  created_at: string;
}

export interface AuditLogOut {
  id: string;
  user_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string;
}
