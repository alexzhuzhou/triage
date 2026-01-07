export interface Case {
  id: string;
  case_number: string;
  patient_name: string;
  exam_type: string;
  exam_date: string | null;
  exam_time: string | null;
  exam_location: string | null;
  referring_party: string | null;
  referring_email: string | null;
  report_due_date: string | null;
  status: 'pending' | 'confirmed' | 'completed';
  extraction_confidence: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  attachments: Attachment[];
  emails: Email[];
}

export interface Email {
  id: string;
  case_id: string | null;
  subject: string;
  sender: string;
  recipients: string[];
  body: string;
  received_at: string;
  processing_status: 'pending' | 'processing' | 'processed' | 'failed';
  raw_extraction: Record<string, any> | null;
  error_message: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface Attachment {
  id: string;
  filename: string;
  content_type: string | null;
  category: 'medical_records' | 'declaration' | 'cover_letter' | 'other';
  category_reason: string | null;
  content_preview: string | null;
  file_path: string | null;
  file_size: number | null;
  storage_provider: string | null;
  created_at: string;
}

export interface CaseFilters {
  status?: string;
  exam_type?: string;
  min_confidence?: number;
  search?: string;
}

export interface BatchProcessResult {
  processed: number;
  failed: number;
  emails: Array<{
    filename: string;
    email_id?: string;
    case_id?: string;
    status?: string;
    error?: string;
  }>;
}

export interface QueueStatus {
  queue: string;
  counts: {
    queued: number;
    started: number;
    finished: number;
    failed: number;
    scheduled: number;
    deferred: number;
  };
  is_empty: boolean;
  worker_count: number;
  total_jobs: number;
}

export interface QueueHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  redis_connected: boolean;
  worker_count: number;
  workers: string[];
  message: string;
  error?: string;
}

export interface RetryResult {
  email_id: string;
  job_id: string;
  status: string;
  message: string;
  previous_error?: string;
}

export interface RetryAllResult {
  retried: number;
  failed_to_retry: number;
  emails: Array<{
    email_id: string;
    job_id?: string;
    subject: string;
    status?: string;
    error?: string;
  }>;
}
