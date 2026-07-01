// services/employment.ts
import api from '@/lib/axios';
import type {
  JobListing,
  JobApplication,
  EmploymentContract,
  AttendanceRecord,
  LeaveRequest,
  PayrollRecord,
} from '@/types/employment';

// ========== Jobs ==========
export const getOpenJobs = (params?: { employment_type?: string; skip?: number; limit?: number }) =>
  api.get<JobListing[]>('/employment/jobs/open', { params });

export const getMyJobs = (params?: { skip?: number; limit?: number }) =>
  api.get<JobListing[]>('/employment/jobs/my', { params });

export const getJob = (jobId: number) => api.get<JobListing>(`/employment/jobs/${jobId}`);

export const createJob = (data: Partial<JobListing>) =>
  api.post<JobListing>('/employment/jobs', data);

export const updateJob = (jobId: number, data: Partial<JobListing>) =>
  api.put<JobListing>(`/employment/jobs/${jobId}`, data);

export const closeJob = (jobId: number) => api.delete(`/employment/jobs/${jobId}`);

// ========== Applications ==========
export const applyToJob = (data: { job_id: number; cover_letter?: string; resume_url?: string }) =>
  api.post<JobApplication>('/employment/applications', data);

export const getMyApplications = (params?: { skip?: number; limit?: number }) =>
  api.get<JobApplication[]>('/employment/applications/my', { params });

export const getJobApplications = (jobId: number, params?: { skip?: number; limit?: number }) =>
  api.get<JobApplication[]>(`/employment/applications/job/${jobId}`, { params });

export const reviewApplication = (applicationId: number, approve: boolean) =>
  api.post<JobApplication>(`/employment/applications/${applicationId}/review?approve=${approve}`);

// ========== Contracts ==========
export const createContract = (data: Partial<EmploymentContract>, idempotencyKey?: string) =>
  api.post<EmploymentContract>('/employment/contracts', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const getMyContract = () => api.get<EmploymentContract>('/employment/contracts/me');

export const getContract = (contractId: number) =>
  api.get<EmploymentContract>(`/employment/contracts/${contractId}`);

export const signContract = (contractId: number, signature_tx_hash: string) =>
  api.post(`/employment/contracts/${contractId}/sign`, { contract_id: contractId, signature_tx_hash });

// ========== Attendance ==========
export const checkIn = (contractId: number, data: { latitude: number; longitude: number; device_fingerprint?: string }) =>
  api.post(`/employment/attendance/check-in?contract_id=${contractId}`, data);

export const checkOut = (contractId: number, data?: { latitude?: number; longitude?: number }) =>
  api.post(`/employment/attendance/check-out?contract_id=${contractId}`, data || {});

export const getMyAttendance = (contractId: number, params?: { skip?: number; limit?: number }) =>
  api.get<AttendanceRecord[]>(`/employment/attendance/my?contract_id=${contractId}`, { params });

// ========== Leave ==========
export const requestLeave = (data: { leave_type: string; start_date: string; end_date: string; reason?: string }) =>
  api.post<LeaveRequest>('/employment/leaves/request', data);

export const getPendingLeaves = () => api.get<LeaveRequest[]>('/employment/leaves/pending');

export const approveLeave = (leaveId: number, approve: boolean) =>
  api.post(`/employment/leaves/${leaveId}/approve?approve=${approve}`);

export const getMyLeaves = (params?: { skip?: number; limit?: number }) =>
  api.get<LeaveRequest[]>('/employment/leaves/my', { params });

// ========== Payroll ==========
export const generatePayroll = (contractId: number, month: string, idempotencyKey?: string) =>
  api.post<PayrollRecord>(
    `/employment/payroll/generate?contract_id=${contractId}&month=${month}`,
    {},
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

export const approvePayroll = (payrollId: number) =>
  api.post<PayrollRecord>(`/employment/payroll/${payrollId}/approve`);

export const payPayroll = (payrollId: number, idempotencyKey?: string) =>
  api.post<PayrollRecord>(
    `/employment/payroll/${payrollId}/pay`,
    {},
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

export const getMyPayrolls = (params?: { skip?: number; limit?: number }) =>
  api.get<PayrollRecord[]>('/employment/payroll/my', { params });