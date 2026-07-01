// types/employment.ts
export type EmploymentStatus = 'WAITING_SIGNATURE' | 'PROBATION' | 'ACTIVE' | 'SUSPENDED' | 'TERMINATED';
export type LeaveType = 'ANNUAL' | 'SICK' | 'UNPAID' | 'MATERNITY' | 'BEREAVEMENT';
export type PayrollStatus = 'DRAFT' | 'APPROVED' | 'PAID';
export type AttendanceStatus = 'PRESENT' | 'ABSENT' | 'LATE' | 'HALF_DAY';
export type ApplicationStatus = 'PENDING' | 'REVIEWING' | 'APPROVED' | 'REJECTED';

export interface JobListing {
  id: number;
  employer_id: number;
  title: string;
  description?: string;
  required_skills: string[];
  required_certificate_ids: number[];
  required_rank?: string;
  salary_min?: number;
  salary_max?: number;
  currency: string;
  location?: string;
  employment_type: string;
  is_active: boolean;
  created_at: string;
}

export interface JobApplication {
  id: number;
  job_id: number;
  applicant_id: number;
  cover_letter?: string;
  resume_url?: string;
  ai_match_score?: number;
  status: ApplicationStatus;
  reviewed_by_id?: number;
  reviewed_at?: string;
  created_at: string;
}

export interface EmploymentContract {
  id: number;
  application_id: number;
  employee_id: number;
  employer_id: number;
  job_title: string;
  base_salary: number;
  allowances: Record<string, number>;
  currency: string;
  start_date: string;
  end_date?: string;
  probation_days: number;
  annual_leave_days: number;
  status: EmploymentStatus;
  smart_contract_address?: string;
  signature_tx_hash?: string;
  employer_signature_tx?: string;
  created_at: string;
}

export interface AttendanceRecord {
  id: number;
  contract_id: number;
  date: string;
  check_in?: string;
  check_out?: string;
  hours_worked: number;
  overtime_hours: number;
  status: AttendanceStatus;
}

export interface LeaveRequest {
  id: number;
  contract_id: number;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  reason?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  approved_by_id?: number;
  approved_at?: string;
  created_at: string;
}

export interface PayrollRecord {
  id: number;
  contract_id: number;
  month: string;
  base_salary: number;
  bonuses: number;
  overtime_pay: number;
  deductions: Record<string, number>;
  net_salary: number;
  status: PayrollStatus;
  payment_tx_hash?: string;
  created_at: string;
}