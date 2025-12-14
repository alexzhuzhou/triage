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
