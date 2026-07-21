// services/employment.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type JobListingCreate = components['schemas']['JobListingCreate'];
type JobListingResponse = components['schemas']['JobListingResponse'];
type JobApplicationCreate = components['schemas']['JobApplicationCreate'];
type JobApplicationResponse = components['schemas']['JobApplicationResponse'];
type EmploymentContractCreate = components['schemas']['EmploymentContractCreate'];
type EmploymentContractResponse = components['schemas']['EmploymentContractResponse'];
type ContractSignRequest = components['schemas']['app__domains__employment__schemas__ContractSignRequest'];
type AttendanceCheckIn = components['schemas']['AttendanceCheckIn'];
type AttendanceRecordResponse = components['schemas']['AttendanceRecordResponse'];
type LeaveRequestCreate = components['schemas']['LeaveRequestCreate'];
type LeaveRequestResponse = components['schemas']['LeaveRequestResponse'];
type PayrollRecordResponse = components['schemas']['PayrollRecordResponse'];

export const EmploymentService = {
  /**
   * إنشاء وظيفة جديدة (لأصحاب العمل)
   * POST /employment/employment/jobs
   * تدعم X-Tenant-ID
   */
  createJob: async (data: JobListingCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<JobListingResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<JobListingResponse>("/employment/employment/jobs", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الوظيفة");
    }
  },

  /**
   * جلب الوظائف النشطة المتاحة للتقديم
   * GET /employment/employment/jobs/open
   * تدعم X-Tenant-ID
   */
  getOpenJobs: async (
    params?: {
      employment_type?: string | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<JobListingResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<JobListingResponse[]>("/employment/employment/jobs/open", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الوظائف النشطة");
    }
  },

  /**
   * جلب الوظائف التي نشرها المستخدم (لأصحاب العمل)
   * GET /employment/employment/jobs/my
   */
  getMyJobs: async (params?: { skip?: number; limit?: number }): Promise<JobListingResponse[]> => {
    try {
      const { data } = await apiClient.get<JobListingResponse[]>("/employment/employment/jobs/my", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب وظائفي");
    }
  },

  /**
   * تحديث وظيفة موجودة (لصاحب العمل)
   * PUT /employment/employment/jobs/{job_id}
   */
  updateJob: async (jobId: number, data: JobListingCreate): Promise<JobListingResponse> => {
    try {
      const id = Number(jobId);
      if (isNaN(id)) throw new Error("معرف الوظيفة غير صحيح");
      const { data: result } = await apiClient.put<JobListingResponse>(`/employment/employment/jobs/${id}`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الوظيفة");
    }
  },

  /**
   * إغلاق وظيفة (وقف استقبال الطلبات)
   * DELETE /employment/employment/jobs/{job_id}
   */
  closeJob: async (jobId: number): Promise<void> => {
    try {
      const id = Number(jobId);
      if (isNaN(id)) throw new Error("معرف الوظيفة غير صحيح");
      await apiClient.delete(`/employment/employment/jobs/${id}`, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إغلاق الوظيفة");
    }
  },

  /**
   * تقديم طلب وظيفة (للمستخدمين العاديين)
   * POST /employment/employment/applications
   * تدعم X-Tenant-ID
   */
  applyToJob: async (data: JobApplicationCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<JobApplicationResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<JobApplicationResponse>("/employment/employment/applications", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تقديم طلب الوظيفة");
    }
  },

  /**
   * جلب طلبات التوظيف الخاصة بي
   * GET /employment/employment/applications/my
   */
  getMyApplications: async (params?: { skip?: number; limit?: number }): Promise<JobApplicationResponse[]> => {
    try {
      const { data } = await apiClient.get<JobApplicationResponse[]>("/employment/employment/applications/my", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب طلباتي");
    }
  },

  /**
   * جلب طلبات التوظيف لوظيفة معينة (لصاحب العمل)
   * GET /employment/employment/applications/job/{job_id}
   */
  getJobApplications: async (jobId: number, params?: { skip?: number; limit?: number }): Promise<JobApplicationResponse[]> => {
    try {
      const id = Number(jobId);
      if (isNaN(id)) throw new Error("معرف الوظيفة غير صحيح");
      const { data } = await apiClient.get<JobApplicationResponse[]>(`/employment/employment/applications/job/${id}`, {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب طلبات الوظيفة");
    }
  },

  /**
   * قبول أو رفض طلب وظيفة (لصاحب العمل)
   * POST /employment/employment/applications/{application_id}/review
   */
  reviewApplication: async (applicationId: number, approve: boolean): Promise<JobApplicationResponse> => {
    try {
      const id = Number(applicationId);
      if (isNaN(id)) throw new Error("معرف الطلب غير صحيح");
      const { data: result } = await apiClient.post<JobApplicationResponse>(
        `/employment/employment/applications/${id}/review`,
        undefined,
        {
          params: { approve },
          withCredentials: true,
        }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل مراجعة الطلب");
    }
  },

  /**
   * إنشاء عقد عمل بعد قبول طلب التوظيف (لصاحب العمل)
   * POST /employment/employment/contracts
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createContract: async (
    data: EmploymentContractCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<EmploymentContractResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<EmploymentContractResponse>(
        "/employment/employment/contracts",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء العقد");
    }
  },

  /**
   * جلب العقد النشط للموظف الحالي
   * GET /employment/employment/contracts/me
   */
  getMyActiveContract: async (): Promise<EmploymentContractResponse> => {
    try {
      const { data } = await apiClient.get<EmploymentContractResponse>("/employment/employment/contracts/me", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب العقد النشط");
    }
  },

  /**
   * توقيع العقد (للموظف أو صاحب العمل)
   * POST /employment/employment/contracts/{contract_id}/sign
   */
  signContract: async (contractId: number, data: ContractSignRequest): Promise<void> => {
    try {
      const id = Number(contractId);
      if (isNaN(id)) throw new Error("معرف العقد غير صحيح");
      await apiClient.post(`/employment/employment/contracts/${id}/sign`, data, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل توقيع العقد");
    }
  },

  /**
   * تسجيل حضور الموظف (مع التحقق من الموقع الجغرافي)
   * POST /employment/employment/attendance/check-in
   */
  checkIn: async (contractId: number, data: AttendanceCheckIn): Promise<void> => {
    try {
      const id = Number(contractId);
      if (isNaN(id)) throw new Error("معرف العقد غير صحيح");
      await apiClient.post("/employment/employment/attendance/check-in", data, {
        params: { contract_id: id },
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تسجيل الحضور");
    }
  },

  /**
   * تسجيل انصراف الموظف وحساب ساعات العمل
   * POST /employment/employment/attendance/check-out
   */
  checkOut: async (contractId: number, location?: AttendanceCheckIn | null): Promise<void> => {
    try {
      const id = Number(contractId);
      if (isNaN(id)) throw new Error("معرف العقد غير صحيح");
      await apiClient.post("/employment/employment/attendance/check-out", location || undefined, {
        params: { contract_id: id },
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تسجيل الانصراف");
    }
  },

  /**
   * جلب سجل الحضور الخاص بي لعقد معين
   * GET /employment/employment/attendance/my
   */
  getMyAttendance: async (contractId: number, params?: { skip?: number; limit?: number }): Promise<AttendanceRecordResponse[]> => {
    try {
      const id = Number(contractId);
      if (isNaN(id)) throw new Error("معرف العقد غير صحيح");
      const { data } = await apiClient.get<AttendanceRecordResponse[]>("/employment/employment/attendance/my", {
        params: { ...params, contract_id: id },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب سجل الحضور");
    }
  },

  /**
   * تقديم طلب إجازة
   * POST /employment/employment/leaves/request
   */
  requestLeave: async (data: LeaveRequestCreate): Promise<LeaveRequestResponse> => {
    try {
      const { data: result } = await apiClient.post<LeaveRequestResponse>("/employment/employment/leaves/request", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تقديم طلب الإجازة");
    }
  },

  /**
   * جلب طلبات الإجازات المعلقة لجميع عقود صاحب العمل
   * GET /employment/employment/leaves/pending
   */
  getPendingLeavesForEmployer: async (): Promise<LeaveRequestResponse[]> => {
    try {
      const { data } = await apiClient.get<LeaveRequestResponse[]>("/employment/employment/leaves/pending", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب طلبات الإجازات المعلقة");
    }
  },

  /**
   * الموافقة أو رفض طلب إجازة (لصاحب العمل)
   * POST /employment/employment/leaves/{leave_id}/approve
   */
  approveLeave: async (leaveId: number, approve: boolean): Promise<void> => {
    try {
      const id = Number(leaveId);
      if (isNaN(id)) throw new Error("معرف طلب الإجازة غير صحيح");
      await apiClient.post(`/employment/employment/leaves/${id}/approve`, undefined, {
        params: { approve },
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل معالجة طلب الإجازة");
    }
  },

  /**
   * إنشاء كشف راتب لشهر محدد (لصاحب العمل)
   * POST /employment/employment/payroll/generate
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  generatePayroll: async (
    contractId: number,
    month: string,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<PayrollRecordResponse> => {
    try {
      const id = Number(contractId);
      if (isNaN(id)) throw new Error("معرف العقد غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<PayrollRecordResponse>(
        "/employment/employment/payroll/generate",
        undefined,
        {
          params: { contract_id: id, month },
          headers: reqHeaders,
          withCredentials: true,
        }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء كشف الراتب");
    }
  },

  /**
   * اعتماد كشف الراتب قبل الدفع
   * POST /employment/employment/payroll/{payroll_id}/approve
   */
  approvePayroll: async (payrollId: number): Promise<PayrollRecordResponse> => {
    try {
      const id = Number(payrollId);
      if (isNaN(id)) throw new Error("معرف كشف الراتب غير صحيح");
      const { data: result } = await apiClient.post<PayrollRecordResponse>(
        `/employment/employment/payroll/${id}/approve`,
        undefined,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل اعتماد كشف الراتب");
    }
  },

  /**
   * دفع الراتب (تحويل من محفظة صاحب العمل إلى محفظة الموظف)
   * POST /employment/employment/payroll/{payroll_id}/pay
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  payPayroll: async (
    payrollId: number,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<PayrollRecordResponse> => {
    try {
      const id = Number(payrollId);
      if (isNaN(id)) throw new Error("معرف كشف الراتب غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<PayrollRecordResponse>(
        `/employment/employment/payroll/${id}/pay`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل دفع الراتب");
    }
  },

  /**
   * جلب كشوف رواتب الموظف الحالي
   * GET /employment/employment/payroll/my
   */
  getMyPayrolls: async (params?: { skip?: number; limit?: number }): Promise<PayrollRecordResponse[]> => {
    try {
      const { data } = await apiClient.get<PayrollRecordResponse[]>("/employment/employment/payroll/my", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب كشوف الرواتب");
    }
  },
};