// services/academy.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

// استخراج الأنواع من components
type TenantCreate = components['schemas']['TenantCreate'];
type TenantResponse = components['schemas']['TenantResponse'];
type OrganizationEntityCreate = components['schemas']['OrganizationEntityCreate'];
type OrganizationEntityResponse = components['schemas']['OrganizationEntityResponse'];
type BootcampCreate = components['schemas']['BootcampCreate'];
type BootcampResponse = components['schemas']['BootcampResponse'];
type TrackCreate = components['schemas']['TrackCreate'];
type TrackResponse = components['schemas']['TrackResponse'];
type CohortCreate = components['schemas']['CohortCreate'];
type CohortResponse = components['schemas']['CohortResponse'];
type CourseCreate = components['schemas']['CourseCreate'];
type CourseResponse = components['schemas']['CourseResponse'];
type CourseUpdate = components['schemas']['CourseUpdate'];
type EnrollmentCreate = components['schemas']['EnrollmentCreate'];
type EnrollmentResponse = components['schemas']['EnrollmentResponse'];
type ProgressUpdate = components['schemas']['ProgressUpdate'];
type CourseUnitCreate = components['schemas']['CourseUnitCreate'];
type CourseUnitResponse = components['schemas']['CourseUnitResponse'];
type UpdateTitleSchema = components['schemas']['UpdateTitleSchema'];
type KnowledgeNodeCreate = components['schemas']['KnowledgeNodeCreate'];
type KnowledgeNodeResponse = components['schemas']['KnowledgeNodeResponse'];
type LiveSessionCreate = components['schemas']['LiveSessionCreate'];
type LiveSessionResponse = components['schemas']['LiveSessionResponse'];
type NodeMaterialCreate = components['schemas']['NodeMaterialCreate'];
type NodeMaterialResponse = components['schemas']['NodeMaterialResponse'];
type QuizCreate = components['schemas']['QuizCreate'];
type QuizResponse = components['schemas']['QuizResponse'];
type TaskCreate = components['schemas']['TaskCreate'];
type TaskResponse = components['schemas']['TaskResponse'];
type TaskSubmissionCreate = components['schemas']['TaskSubmissionCreate'];
type TaskSubmissionResponse = components['schemas']['TaskSubmissionResponse'];
type TaskGradeUpdate = components['schemas']['TaskGradeUpdate'];
type FinancialSummaryResponse = components['schemas']['FinancialSummaryResponse'];
type StudentDigitalTwinResponse = components['schemas']['StudentDigitalTwinResponse'];

export const AcademyService = {
  // ==========================================
  // 1. الكورسات (Courses)
  // ==========================================
  /**
   * جلب قائمة الكورسات (للمشرفين أو المدربين)
   * GET /academy/courses
   */
  getCourses: async (skip: number = 0, limit: number = 20): Promise<CourseResponse[]> => {
    try {
      const { data } = await apiClient.get<CourseResponse[]>("/academy/courses", {
        params: { skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الكورسات");
    }
  },

  /**
   * جلب الكورسات المتاحة في المتجر (للمستخدم الحالي)
   * GET /academy/store/courses
   */
  getStoreCourses: async (skip: number = 0, limit: number = 20): Promise<CourseResponse[]> => {
    try {
      const { data } = await apiClient.get<CourseResponse[]>("/academy/store/courses", {
        params: { skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الكورسات من المتجر");
    }
  },

  /**
   * جلب تفاصيل كورس معين
   * GET /academy/courses/{course_id}
   * يتطلب identifier في query
   */
  getCourseById: async (courseId: number, identifier: string): Promise<CourseResponse> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data } = await apiClient.get<CourseResponse>(`/academy/courses/${id}`, {
        params: { identifier },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الكورس");
    }
  },

  /**
   * إنشاء كورس جديد
   * POST /academy/courses
   */
  createCourse: async (data: CourseCreate): Promise<CourseResponse> => {
    try {
      const { data: result } = await apiClient.post<CourseResponse>("/academy/courses", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الكورس");
    }
  },

  /**
   * تحديث كورس
   * PUT /academy/courses/{course_id}
   */
  updateCourse: async (courseId: number, data: CourseUpdate): Promise<CourseResponse> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data: result } = await apiClient.put<CourseResponse>(`/academy/courses/${id}`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الكورس");
    }
  },

  // ==========================================
  // 2. الوحدات (Units)
  // ==========================================
  /**
   * جلب وحدات كورس معين
   * GET /academy/courses/{course_id}/units
   */
  getCourseUnits: async (courseId: number, skip: number = 0, limit: number = 100): Promise<CourseUnitResponse[]> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data } = await apiClient.get<CourseUnitResponse[]>(`/academy/courses/${id}/units`, {
        params: { skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب وحدات الكورس");
    }
  },

  /**
   * إنشاء وحدة جديدة داخل كورس
   * POST /academy/courses/{course_id}/units
   */
  createCourseUnit: async (courseId: number, data: CourseUnitCreate): Promise<CourseUnitResponse> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data: result } = await apiClient.post<CourseUnitResponse>(`/academy/courses/${id}/units`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الوحدة");
    }
  },

  /**
   * تحديث عنوان وحدة
   * PUT /academy/units/{unit_id}
   */
  updateCourseUnit: async (unitId: number, data: UpdateTitleSchema): Promise<CourseUnitResponse> => {
    try {
      const id = Number(unitId);
      if (isNaN(id)) throw new Error("معرف الوحدة غير صحيح");
      const { data: result } = await apiClient.put<CourseUnitResponse>(`/academy/units/${id}`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الوحدة");
    }
  },

  /**
   * حذف وحدة
   * DELETE /academy/units/{unit_id}
   */
  deleteCourseUnit: async (unitId: number): Promise<void> => {
    try {
      const id = Number(unitId);
      if (isNaN(id)) throw new Error("معرف الوحدة غير صحيح");
      await apiClient.delete(`/academy/units/${id}`, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف الوحدة");
    }
  },

  // ==========================================
  // 3. العقد المعرفية (Nodes)
  // ==========================================
  /**
   * إنشاء عقدة معرفية (درس)
   * POST /academy/nodes
   */
  createKnowledgeNode: async (data: KnowledgeNodeCreate): Promise<KnowledgeNodeResponse> => {
    try {
      const { data: result } = await apiClient.post<KnowledgeNodeResponse>("/academy/nodes", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الدرس");
    }
  },

  /**
   * جلب العقد المعرفية لكورس معين
   * GET /academy/courses/{course_id}/nodes
   */
  getCourseNodes: async (courseId: number, skip: number = 0, limit: number = 100): Promise<KnowledgeNodeResponse[]> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data } = await apiClient.get<KnowledgeNodeResponse[]>(`/academy/courses/${id}/nodes`, {
        params: { skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب دروس الكورس");
    }
  },

  /**
   * تحديث عنوان عقدة معرفية
   * PUT /academy/nodes/{node_id}
   */
  updateKnowledgeNode: async (nodeId: number, data: UpdateTitleSchema): Promise<KnowledgeNodeResponse> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data: result } = await apiClient.put<KnowledgeNodeResponse>(`/academy/nodes/${id}`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الدرس");
    }
  },

  /**
   * حذف عقدة معرفية
   * DELETE /academy/nodes/{node_id}
   */
  deleteKnowledgeNode: async (nodeId: number): Promise<void> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      await apiClient.delete(`/academy/nodes/${id}`, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف الدرس");
    }
  },

  // ==========================================
  // 4. مواد الدرس (Materials)
  // ==========================================
  /**
   * إنشاء مادة لدرس معين
   * POST /academy/nodes/{node_id}/materials
   */
  createNodeMaterial: async (nodeId: number, data: NodeMaterialCreate): Promise<NodeMaterialResponse> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data: result } = await apiClient.post<NodeMaterialResponse>(`/academy/nodes/${id}/materials`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة مادة للدرس");
    }
  },

  /**
   * جلب مواد درس معين
   * GET /academy/nodes/{node_id}/materials
   */
  getNodeMaterials: async (nodeId: number): Promise<NodeMaterialResponse[]> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data } = await apiClient.get<NodeMaterialResponse[]>(`/academy/nodes/${id}/materials`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب مواد الدرس");
    }
  },

  // ==========================================
  // 5. الاختبارات (Quizzes)
  // ==========================================
  /**
   * إنشاء اختبار لدرس معين
   * POST /academy/nodes/{node_id}/quiz
   */
  createQuiz: async (nodeId: number, data: QuizCreate): Promise<QuizResponse> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data: result } = await apiClient.post<QuizResponse>(`/academy/nodes/${id}/quiz`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الاختبار");
    }
  },

  // ==========================================
  // 6. الجلسات الحية (Live Sessions)
  // ==========================================
  /**
   * إنشاء جلسة حية لدرس معين
   * POST /academy/nodes/{node_id}/live
   */
  createLiveSession: async (nodeId: number, data: LiveSessionCreate): Promise<LiveSessionResponse> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data: result } = await apiClient.post<LiveSessionResponse>(`/academy/nodes/${id}/live`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الجلسة الحية");
    }
  },

  // ==========================================
  // 7. التكليفات (Tasks)
  // ==========================================
  /**
   * إنشاء تكليف جديد
   * POST /academy/tasks
   */
  createTask: async (data: TaskCreate): Promise<TaskResponse> => {
    try {
      const { data: result } = await apiClient.post<TaskResponse>("/academy/tasks", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء التكليف");
    }
  },

  /**
   * جلب تكليفات كورس معين
   * GET /academy/courses/{course_id}/tasks
   */
  getCourseTasks: async (courseId: number, skip: number = 0, limit: number = 100): Promise<TaskResponse[]> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data } = await apiClient.get<TaskResponse[]>(`/academy/courses/${id}/tasks`, {
        params: { skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تكليفات الكورس");
    }
  },

  /**
   * تسليم تكليف (للطالب)
   * POST /academy/tasks/{task_id}/submit
   */
  submitTask: async (taskId: number, data: TaskSubmissionCreate): Promise<TaskSubmissionResponse> => {
    try {
      const id = Number(taskId);
      if (isNaN(id)) throw new Error("معرف التكليف غير صحيح");
      const { data: result } = await apiClient.post<TaskSubmissionResponse>(`/academy/tasks/${id}/submit`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسليم المهمة");
    }
  },

  /**
   * جلب تسليمات طلاب لتكليف معين (للمدرب)
   * GET /academy/instructor/tasks/{task_id}/submissions
   */
  getTaskSubmissions: async (taskId: number, skip: number = 0, limit: number = 100): Promise<TaskSubmissionResponse[]> => {
    try {
      const id = Number(taskId);
      if (isNaN(id)) throw new Error("معرف التكليف غير صحيح");
      const { data } = await apiClient.get<TaskSubmissionResponse[]>(`/academy/instructor/tasks/${id}/submissions`, {
        params: { skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تسليمات الطلاب");
    }
  },

  /**
   * تقييم تسليم طالب (للمدرب)
   * PUT /academy/instructor/submissions/{submission_id}/grade
   */
  gradeSubmission: async (submissionId: number, data: TaskGradeUpdate): Promise<TaskSubmissionResponse> => {
    try {
      const id = Number(submissionId);
      if (isNaN(id)) throw new Error("معرف التسليم غير صحيح");
      const { data: result } = await apiClient.put<TaskSubmissionResponse>(`/academy/instructor/submissions/${id}/grade`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تقييم التسليم");
    }
  },

  /**
   * جلب تسليماتي (للطالب)
   * GET /academy/student/my-submissions
   */
  getMySubmissions: async (skip: number = 0, limit: number = 100): Promise<TaskSubmissionResponse[]> => {
    try {
      const { data } = await apiClient.get<TaskSubmissionResponse[]>("/academy/student/my-submissions", {
        params: { skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تسليماتي");
    }
  },

  // ==========================================
  // 8. إحصائيات المدرب (Instructor Stats) ✅ جديدة
  // ==========================================
  /**
   * جلب إحصائيات المدرب الحالي
   * GET /academy/instructor/stats
   */
  getInstructorStats: async (): Promise<{
    total_courses: number;
    total_students: number;
    pending_submissions: number;
    total_certificates: number;
  }> => {
    try {
      const { data } = await apiClient.get<{
        total_courses: number;
        total_students: number;
        pending_submissions: number;
        total_certificates: number;
      }>("/academy/instructor/stats", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب إحصائيات المدرب");
    }
  },

  // ==========================================
  // 9. اشتراكات الطالب (Enrollments)
  // ==========================================
  /**
   * جلب اشتراكاتي (الكورسات المسجل فيها)
   * GET /academy/student/my-enrollments
   */
  getMyEnrollments: async (skip: number = 0, limit: number = 100): Promise<EnrollmentResponse[]> => {
    try {
      const { data } = await apiClient.get<EnrollmentResponse[]>("/academy/student/my-enrollments", {
        params: { skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب اشتراكاتك");
    }
  },

  /**
   * التسجيل في كورس (شراء أو انضمام)
   * POST /academy/store/courses/{course_id}/enroll
   */
  enrollInCourse: async (courseId: number, data: EnrollmentCreate): Promise<EnrollmentResponse> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data: result } = await apiClient.post<EnrollmentResponse>(`/academy/store/courses/${id}/enroll`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل التسجيل في الكورس");
    }
  },

  /**
   * التسجيل في كورس (طريقة مبسطة بدون بيانات إضافية)
   * POST /academy/enroll?course_id={courseId}
   */
  enrollInCourseSimple: async (courseId: number): Promise<EnrollmentResponse> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data: result } = await apiClient.post<EnrollmentResponse>(
        "/academy/enroll",
        undefined,
        {
          params: { course_id: id },
          withCredentials: true,
        }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل التسجيل في الكورس");
    }
  },

  /**
   * تحديث التقدم في كورس (للطالب)
   * PUT /academy/student/enrollments/{course_id}/progress
   */
  updateProgress: async (courseId: number, data: ProgressUpdate): Promise<EnrollmentResponse> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data: result } = await apiClient.put<EnrollmentResponse>(`/academy/student/enrollments/${id}/progress`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث التقدم");
    }
  },

  // ==========================================
  // 10. المستأجر (Tenant) والكيانات التنظيمية
  // ==========================================
  /**
   * جلب المستأجر بواسطة النطاق (يجب تمرير domain)
   * GET /academy/tenants/by-domain?domain=...
   */
  getTenantByDomain: async (domain: string, identifier?: string, maxRequests?: number, windowSeconds?: number): Promise<TenantResponse | null> => {
    if (!domain || domain.trim() === '') {
      console.error("❌ getTenantByDomain: 'domain' parameter is missing or empty!");
      throw new Error("معامل 'domain' مطلوب للبحث عن المستأجر");
    }

    console.log(`🔍 getTenantByDomain: searching for domain = "${domain}"`);

    try {
      const params: Record<string, any> = { domain: domain.trim() };
      if (identifier) params.identifier = identifier;
      if (maxRequests !== undefined) params.max_requests = maxRequests;
      if (windowSeconds !== undefined) params.window_seconds = windowSeconds;

      const { data } = await apiClient.get<TenantResponse>("/academy/tenants/by-domain", {
        params,
        withCredentials: true,
      });
      console.log("✅ Tenant found:", data);
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        console.warn(`⚠️ Tenant with domain "${domain}" not found (404)`);
        return null;
      }
      console.error("❌ Error fetching tenant:", error);
      throw handleError(error, "فشل جلب بيانات المستأجر");
    }
  },

  /**
   * إنشاء مستأجر جديد
   * POST /academy/tenants
   */
  createTenant: async (data: TenantCreate): Promise<TenantResponse> => {
    try {
      const { data: result } = await apiClient.post<TenantResponse>("/academy/tenants", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المستأجر");
    }
  },

  /**
   * جلب الكيانات التنظيمية (للمستأجر الحالي)
   * GET /academy/entities
   */
  getOrganizationEntities: async (tenantId: number, skip: number = 0, limit: number = 100): Promise<OrganizationEntityResponse[]> => {
    try {
      const { data } = await apiClient.get<OrganizationEntityResponse[]>("/academy/entities", {
        params: { tenant_id: tenantId, skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الهيكل التنظيمي");
    }
  },

  /**
   * إنشاء كيان تنظيمي جديد
   * POST /academy/entities
   */
  createOrganizationEntity: async (data: OrganizationEntityCreate): Promise<OrganizationEntityResponse> => {
    try {
      const { data: result } = await apiClient.post<OrganizationEntityResponse>("/academy/entities", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الكيان التنظيمي");
    }
  },

  // ==========================================
  // 11. المعسكرات (Bootcamps)
  // ==========================================
  /**
   * جلب المعسكرات
   * GET /academy/bootcamps
   */
  getBootcamps: async (orgEntityId?: number, skip: number = 0, limit: number = 100): Promise<BootcampResponse[]> => {
    try {
      const { data } = await apiClient.get<BootcampResponse[]>("/academy/bootcamps", {
        params: { org_entity_id: orgEntityId, skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المعسكرات");
    }
  },

  /**
   * إنشاء معسكر جديد
   * POST /academy/bootcamps
   */
  createBootcamp: async (data: BootcampCreate): Promise<BootcampResponse> => {
    try {
      const { data: result } = await apiClient.post<BootcampResponse>("/academy/bootcamps", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المعسكر");
    }
  },

  // ==========================================
  // 12. المسارات (Tracks)
  // ==========================================
  /**
   * جلب المسارات
   * GET /academy/tracks
   */
  getTracks: async (orgEntityId?: number, bootcampId?: number, skip: number = 0, limit: number = 100): Promise<TrackResponse[]> => {
    try {
      const { data } = await apiClient.get<TrackResponse[]>("/academy/tracks", {
        params: { org_entity_id: orgEntityId, bootcamp_id: bootcampId, skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المسارات");
    }
  },

  /**
   * إنشاء مسار جديد
   * POST /academy/tracks
   */
  createTrack: async (data: TrackCreate): Promise<TrackResponse> => {
    try {
      const { data: result } = await apiClient.post<TrackResponse>("/academy/tracks", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المسار");
    }
  },

  // ==========================================
  // 13. الدفعات (Cohorts)
  // ==========================================
  /**
   * جلب الدفعات
   * GET /academy/cohorts
   */
  getCohorts: async (orgEntityId: number, skip: number = 0, limit: number = 100): Promise<CohortResponse[]> => {
    try {
      const id = Number(orgEntityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<CohortResponse[]>("/academy/cohorts", {
        params: { org_entity_id: id, skip, limit },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الدفعات");
    }
  },

  /**
   * إنشاء دفعة جديدة
   * POST /academy/cohorts
   */
  createCohort: async (data: CohortCreate): Promise<CohortResponse> => {
    try {
      const { data: result } = await apiClient.post<CohortResponse>("/academy/cohorts", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الدفعة");
    }
  },

  // ==========================================
  // 14. رفع الملفات (Upload)
  // ==========================================
  /**
   * رفع ملف (صورة مصغرة للكورس)
   * POST /academy/upload
   */
  uploadFile: async (courseId: number, file: File): Promise<{ file_url?: string }> => {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await apiClient.post<{ file_url?: string }>("/academy/upload", formData, {
        params: { course_id: courseId },
        headers: { "Content-Type": "multipart/form-data" },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل رفع الملف");
    }
  },

  // ==========================================
  // 15. لوحة الشرف (Leaderboard)
  // ==========================================
  /**
   * جلب لوحة المتصدرين
   * GET /academy/leaderboard
   */
  getLeaderboard: async (limit: number = 50, identifier: string, maxRequests?: number, windowSeconds?: number): Promise<unknown> => {
    try {
      const { data } = await apiClient.get<unknown>("/academy/leaderboard", {
        params: { limit, identifier, max_requests: maxRequests, window_seconds: windowSeconds },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب لوحة الشرف");
    }
  },

  // ==========================================
  // 16. التقارير المالية
  // ==========================================
  /**
   * جلب الملخص المالي
   * GET /academy/reports/financial
   */
  getFinancialSummary: async (): Promise<FinancialSummaryResponse> => {
    try {
      const { data } = await apiClient.get<FinancialSummaryResponse>("/academy/reports/financial", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الملخص المالي");
    }
  },

  // ==========================================
  // 17. التوأم الرقمي للطالب
  // ==========================================
  /**
   * جلب التوأم الرقمي للطالب الحالي
   * GET /academy/digital-twin/me
   */
  getMyDigitalTwin: async (): Promise<StudentDigitalTwinResponse> => {
    try {
      const { data } = await apiClient.get<StudentDigitalTwinResponse>("/academy/digital-twin/me", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب التوأم الرقمي");
    }
  },
};