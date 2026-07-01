// services/academy.service.ts
import { apiClient } from "@/lib/api-client";
import {
  Course,
  CourseUnit,
  KnowledgeNode,
  AcademyTask,
  Enrollment,
  TaskSubmission,
  Bootcamp,
  Track,
  Cohort,
  OrganizationEntity,
  LiveSession,
  Certificate,
  Quiz,
  DigitalTwin,
  CameraAnalysis,
  Badge,
  PaginatedResponse,
  EnrollmentPayload,
  ProgressUpdatePayload,
  TaskSubmissionPayload,
  TaskGradePayload,
  InstructorStats,
  GradingStats,
} from "@/types/academy";
import { handleError } from "@/lib/error-handler";

// 🔥 دالة مساعدة لإضافة tenant_id
const getTenantId = (): number => {
  try {
    const stored = localStorage.getItem("auth-storage");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.state?.user?.tenant_id || 1;
    }
  } catch (_) {}
  return 1;
};

export const AcademyService = {
  // ==========================================
  // 1. الكورسات (Courses)
  // ==========================================
  getCourses: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Course>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/courses", {
        params: { tenant_id: tenantId, skip, limit },
      });
      if (Array.isArray(data)) {
        return { data, total: data.length, skip, limit };
      }
      return data as PaginatedResponse<Course>;
    } catch (error) {
      throw handleError(error, "فشل جلب الكورسات");
    }
  },

  getStoreCourses: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Course>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/store/courses", {
        params: { tenant_id: tenantId, skip, limit },
      });
      return data as PaginatedResponse<Course>;
    } catch (error) {
      throw handleError(error, "فشل جلب الكورسات من المتجر");
    }
  },

  getCourseById: async (courseId: number): Promise<Course> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data } = await apiClient.get(`/academy/courses/${id}`);
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الكورس");
    }
  },

  createCourse: async (data: any): Promise<Course> => {
    try {
      const tenantId = getTenantId();
      const { data: result } = await apiClient.post("/academy/courses", {
        ...data,
        tenant_id: tenantId,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الكورس");
    }
  },

  updateCourse: async (courseId: number, data: any): Promise<Course> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data: result } = await apiClient.put(`/academy/courses/${id}`, data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الكورس");
    }
  },

  deleteCourse: async (courseId: number): Promise<void> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      await apiClient.delete(`/academy/courses/${id}`);
    } catch (error) {
      throw handleError(error, "فشل حذف الكورس");
    }
  },

  // ==========================================
  // 2. المنهج (Curriculum)
  // ==========================================
  getCurriculum: async (
    courseId: number
  ): Promise<{ units: CourseUnit[]; nodes: KnowledgeNode[] }> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const [unitsRes, nodesRes] = await Promise.all([
        apiClient.get(`/academy/courses/${id}/units`),
        apiClient.get(`/academy/courses/${id}/nodes`),
      ]);
      return {
        units: unitsRes.data as CourseUnit[],
        nodes: nodesRes.data as KnowledgeNode[],
      };
    } catch (error) {
      throw handleError(error, "فشل جلب المنهج");
    }
  },

  // ==========================================
  // 3. الوحدات (Units)
  // ==========================================
  createCourseUnit: async (courseId: number, data: any): Promise<CourseUnit> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data: result } = await apiClient.post(`/academy/courses/${id}/units`, data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الوحدة");
    }
  },

  updateCourseUnit: async (unitId: number, title: string): Promise<CourseUnit> => {
    try {
      const id = Number(unitId);
      if (isNaN(id)) throw new Error("معرف الوحدة غير صحيح");
      const { data: result } = await apiClient.put(`/academy/units/${id}`, { title });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الوحدة");
    }
  },

  deleteCourseUnit: async (unitId: number): Promise<void> => {
    try {
      const id = Number(unitId);
      if (isNaN(id)) throw new Error("معرف الوحدة غير صحيح");
      await apiClient.delete(`/academy/units/${id}`);
    } catch (error) {
      throw handleError(error, "فشل حذف الوحدة");
    }
  },

  // ==========================================
  // 4. الدروس (Nodes)
  // ==========================================
  createKnowledgeNode: async (
    courseId: number,
    unitId: number,
    data: any
  ): Promise<KnowledgeNode> => {
    try {
      const cid = Number(courseId);
      const uid = Number(unitId);
      if (isNaN(cid) || isNaN(uid)) throw new Error("معرف الكورس أو الوحدة غير صحيح");
      const { data: result } = await apiClient.post("/academy/nodes", {
        ...data,
        course_id: cid,
        unit_id: uid,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الدرس");
    }
  },

  updateKnowledgeNode: async (nodeId: number, title: string): Promise<KnowledgeNode> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data: result } = await apiClient.put(`/academy/nodes/${id}`, { title });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الدرس");
    }
  },

  deleteKnowledgeNode: async (nodeId: number): Promise<void> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      await apiClient.delete(`/academy/nodes/${id}`);
    } catch (error) {
      throw handleError(error, "فشل حذف الدرس");
    }
  },

  // ==========================================
  // 5. مواد الدروس (Materials)
  // ==========================================
  createNodeMaterial: async (nodeId: number, data: any): Promise<any> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data: result } = await apiClient.post(`/academy/nodes/${id}/materials`, data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل ربط المحتوى");
    }
  },

  // ==========================================
  // 6. الاختبارات (Quizzes)
  // ==========================================
  createQuiz: async (nodeId: number, data: any): Promise<Quiz> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data: result } = await apiClient.post(`/academy/nodes/${id}/quiz`, data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الاختبار");
    }
  },

  getQuizByNode: async (nodeId: number): Promise<Quiz> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data } = await apiClient.get(`/academy/nodes/${id}/quiz`);
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الاختبار");
    }
  },

  submitQuiz: async (
    nodeId: number,
    answers: Record<number, string>
  ): Promise<{ score: number; passed: boolean }> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      const { data } = await apiClient.post(`/academy/nodes/${id}/quiz/submit`, { answers });
      return data;
    } catch (error) {
      throw handleError(error, "فشل تقديم الاختبار");
    }
  },

  getQuizResults: async (quizId: number): Promise<any> => {
    try {
      const id = Number(quizId);
      if (isNaN(id)) throw new Error("معرف الاختبار غير صحيح");
      const { data } = await apiClient.get(`/academy/quiz/${id}/results`);
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب نتائج الاختبار");
    }
  },

  // ==========================================
  // 7. التكليفات (Tasks)
  // ==========================================
  getTasks: async (
    courseId: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<AcademyTask>> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data } = await apiClient.get(`/academy/courses/${id}/tasks`, {
        params: { skip, limit },
      });
      return data as PaginatedResponse<AcademyTask>;
    } catch (error) {
      throw handleError(error, "فشل جلب التكليفات");
    }
  },

  createTask: async (data: any): Promise<AcademyTask> => {
    try {
      const { data: result } = await apiClient.post("/academy/tasks", data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء التكليف");
    }
  },

  // ==========================================
  // 8. اشتراكات الطالب (Enrollments)
  // ==========================================
  getMyEnrollments: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Enrollment>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/student/my-enrollments", {
        params: { tenant_id: tenantId, skip, limit },
      });
      return data as PaginatedResponse<Enrollment>;
    } catch (error) {
      throw handleError(error, "فشل جلب اشتراكاتك");
    }
  },

  enrollInCourse: async (
    courseId: number,
    payload: EnrollmentPayload
  ): Promise<Enrollment> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data } = await apiClient.post(`/academy/store/courses/${id}/enroll`, payload);
      return data;
    } catch (error) {
      throw handleError(error, "فشل التسجيل في الكورس");
    }
  },

  updateProgress: async (
    courseId: number,
    payload: ProgressUpdatePayload
  ): Promise<Enrollment> => {
    try {
      const id = Number(courseId);
      if (isNaN(id)) throw new Error("معرف الكورس غير صحيح");
      const { data } = await apiClient.put(
        `/academy/student/enrollments/${id}/progress`,
        payload
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل تحديث التقدم");
    }
  },

  // ==========================================
  // 9. تسليمات التكليفات (Submissions)
  // ==========================================
  submitTask: async (
    taskId: number,
    payload: TaskSubmissionPayload
  ): Promise<TaskSubmission> => {
    try {
      const id = Number(taskId);
      if (isNaN(id)) throw new Error("معرف التكليف غير صحيح");
      const { data } = await apiClient.post(`/academy/tasks/${id}/submit`, payload);
      return data;
    } catch (error) {
      throw handleError(error, "فشل تسليم المهمة");
    }
  },

  getMySubmissions: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<TaskSubmission>> => {
    try {
      const { data } = await apiClient.get("/academy/student/my-submissions", {
        params: { skip, limit },
      });
      return data as PaginatedResponse<TaskSubmission>;
    } catch (error) {
      throw handleError(error, "فشل جلب تسليماتك");
    }
  },

  getPendingSubmissions: async (
    taskId: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<TaskSubmission>> => {
    try {
      const id = Number(taskId);
      if (isNaN(id)) throw new Error("معرف التكليف غير صحيح");
      const { data } = await apiClient.get(
        `/academy/instructor/tasks/${id}/submissions`,
        { params: { skip, limit } }
      );
      return data as PaginatedResponse<TaskSubmission>;
    } catch (error) {
      throw handleError(error, "فشل جلب تسليمات الطلاب");
    }
  },

  gradeSubmission: async (
    submissionId: number,
    payload: TaskGradePayload
  ): Promise<TaskSubmission> => {
    try {
      const id = Number(submissionId);
      if (isNaN(id)) throw new Error("معرف التسليم غير صحيح");
      const { data } = await apiClient.put(
        `/academy/instructor/submissions/${id}/grade`,
        payload
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل تقييم التسليم");
    }
  },

  // ==========================================
  // 10. لوحة الشرف (Leaderboard)
  // ==========================================
  getLeaderboard: async (limit: number = 50): Promise<any[]> => {
    try {
      const { data } = await apiClient.get("/academy/leaderboard", {
        params: { limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب لوحة الشرف");
    }
  },

  // ==========================================
  // 11. المعسكرات والمسارات (Bootcamps & Tracks)
  // ==========================================
  getBootcamps: async (
    orgEntityId?: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Bootcamp>> => {
    try {
      const { data } = await apiClient.get("/academy/bootcamps", {
        params: { org_entity_id: orgEntityId, skip, limit },
      });
      return data as PaginatedResponse<Bootcamp>;
    } catch (error) {
      throw handleError(error, "فشل جلب المعسكرات");
    }
  },

  createBootcamp: async (data: any): Promise<Bootcamp> => {
    try {
      const { data: result } = await apiClient.post("/academy/bootcamps", data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المعسكر");
    }
  },

  getTracks: async (
    orgEntityId?: number,
    bootcampId?: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Track>> => {
    try {
      const { data } = await apiClient.get("/academy/tracks", {
        params: { org_entity_id: orgEntityId, bootcamp_id: bootcampId, skip, limit },
      });
      return data as PaginatedResponse<Track>;
    } catch (error) {
      throw handleError(error, "فشل جلب المسارات");
    }
  },

  createTrack: async (data: any): Promise<Track> => {
    try {
      const { data: result } = await apiClient.post("/academy/tracks", data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المسار");
    }
  },

  // ==========================================
  // 12. الدفعات (Cohorts)
  // ==========================================
  getCohorts: async (
    orgEntityId: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Cohort>> => {
    try {
      const id = Number(orgEntityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get("/academy/cohorts", {
        params: { org_entity_id: id, skip, limit },
      });
      return data as PaginatedResponse<Cohort>;
    } catch (error) {
      throw handleError(error, "فشل جلب الدفعات");
    }
  },

  createCohort: async (data: any): Promise<Cohort> => {
    try {
      const { data: result } = await apiClient.post("/academy/cohorts", data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الدفعة");
    }
  },

  // ==========================================
  // 13. الكيانات التنظيمية (Organization Entities)
  // ==========================================
  getOrganizationEntities: async (
    skip: number = 0,
    limit: number = 100
  ): Promise<PaginatedResponse<OrganizationEntity>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/entities", {
        params: { tenant_id: tenantId, skip, limit },
      });
      return data as PaginatedResponse<OrganizationEntity>;
    } catch (error) {
      throw handleError(error, "فشل جلب الهيكل التنظيمي");
    }
  },

  createOrganizationEntity: async (data: any): Promise<OrganizationEntity> => {
    try {
      const tenantId = getTenantId();
      const { data: result } = await apiClient.post("/academy/entities", {
        ...data,
        tenant_id: tenantId,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الكيان التنظيمي");
    }
  },

  updateOrganizationEntity: async (
    entityId: number,
    data: any
  ): Promise<OrganizationEntity> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data: result } = await apiClient.put(`/academy/entities/${id}`, data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الكيان التنظيمي");
    }
  },

  deleteOrganizationEntity: async (entityId: number): Promise<void> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      await apiClient.delete(`/academy/entities/${id}`);
    } catch (error) {
      throw handleError(error, "فشل حذف الكيان التنظيمي");
    }
  },

  // ==========================================
  // 14. الجلسات الحية (Live Sessions)
  // ==========================================
  getLiveSessions: async (
    orgEntityId?: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<LiveSession>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/live-sessions", {
        params: {
          tenant_id: tenantId,
          org_entity_id: orgEntityId,
          skip,
          limit,
        },
      });
      return data as PaginatedResponse<LiveSession>;
    } catch (error) {
      throw handleError(error, "فشل جلب الجلسات الحية");
    }
  },

  createLiveSession: async (data: any): Promise<LiveSession> => {
    try {
      const tenantId = getTenantId();
      const { data: result } = await apiClient.post("/academy/live-sessions", {
        ...data,
        tenant_id: tenantId,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الجلسة الحية");
    }
  },

  updateLiveSession: async (sessionId: number, data: any): Promise<LiveSession> => {
    try {
      const id = Number(sessionId);
      if (isNaN(id)) throw new Error("معرف الجلسة غير صحيح");
      const { data: result } = await apiClient.put(`/academy/live-sessions/${id}`, data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الجلسة الحية");
    }
  },

  deleteLiveSession: async (sessionId: number): Promise<void> => {
    try {
      const id = Number(sessionId);
      if (isNaN(id)) throw new Error("معرف الجلسة غير صحيح");
      await apiClient.delete(`/academy/live-sessions/${id}`);
    } catch (error) {
      throw handleError(error, "فشل حذف الجلسة الحية");
    }
  },

  joinLiveSession: async (nodeId: number): Promise<void> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف الدرس غير صحيح");
      await apiClient.post(`/academy/nodes/${id}/live/join`);
    } catch (error) {
      throw handleError(error, "فشل الانضمام للبث المباشر");
    }
  },

  // ==========================================
  // 15. الشهادات (Certificates)
  // ==========================================
  getCertificates: async (
    orgEntityId?: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Certificate>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/certificates", {
        params: {
          tenant_id: tenantId,
          org_entity_id: orgEntityId,
          skip,
          limit,
        },
      });
      return data as PaginatedResponse<Certificate>;
    } catch (error) {
      throw handleError(error, "فشل جلب الشهادات");
    }
  },

  getMyCertificates: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Certificate>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/student/certificates", {
        params: { tenant_id: tenantId, skip, limit },
      });
      return data as PaginatedResponse<Certificate>;
    } catch (error) {
      throw handleError(error, "فشل جلب شهاداتك");
    }
  },

  revokeCertificate: async (certificateId: number): Promise<void> => {
    try {
      const id = Number(certificateId);
      if (isNaN(id)) throw new Error("معرف الشهادة غير صحيح");
      await apiClient.post(`/academy/certificates/${id}/revoke`);
    } catch (error) {
      throw handleError(error, "فشل إلغاء الشهادة");
    }
  },

  reissueCertificate: async (certificateId: number): Promise<Certificate> => {
    try {
      const id = Number(certificateId);
      if (isNaN(id)) throw new Error("معرف الشهادة غير صحيح");
      const { data } = await apiClient.post(`/academy/certificates/${id}/reissue`);
      return data;
    } catch (error) {
      throw handleError(error, "فشل إعادة إصدار الشهادة");
    }
  },

  // ==========================================
  // 16. التوائم الرقمية والكاميرات (Digital Twins & Cameras)
  // ==========================================
  getDigitalTwin: async (): Promise<DigitalTwin> => {
    try {
      const { data } = await apiClient.get("/academy/digital-twin/me");
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب التوأم الرقمي");
    }
  },

  getDigitalTwins: async (
    skip: number = 0,
    limit: number = 50
  ): Promise<PaginatedResponse<DigitalTwin>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/digital-twins", {
        params: { tenant_id: tenantId, skip, limit },
      });
      return data as PaginatedResponse<DigitalTwin>;
    } catch (error) {
      throw handleError(error, "فشل جلب التوائم الرقمية");
    }
  },

  getCameraAnalytics: async (
    orgEntityId: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<CameraAnalysis>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/camera-analyses", {
        params: {
          tenant_id: tenantId,
          org_entity_id: orgEntityId,
          skip,
          limit,
        },
      });
      return data as PaginatedResponse<CameraAnalysis>;
    } catch (error) {
      throw handleError(error, "فشل جلب تحليلات الكاميرات");
    }
  },

  // ==========================================
  // 17. إحصائيات المدرب (Instructor Stats)
  // ==========================================
  getInstructorStats: async (): Promise<InstructorStats> => {
    try {
      const { data } = await apiClient.get("/academy/instructor/stats");
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب إحصائيات المدرب");
    }
  },

  getGradingStats: async (): Promise<GradingStats> => {
    try {
      const { data } = await apiClient.get("/academy/instructor/grading-stats");
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب إحصائيات التقييم");
    }
  },

  getInstructorCourses: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Course>> => {
    try {
      const { data } = await apiClient.get("/academy/instructor/courses", {
        params: { skip, limit },
      });
      return data as PaginatedResponse<Course>;
    } catch (error) {
      throw handleError(error, "فشل جلب كورسات المدرب");
    }
  },

  // ==========================================
  // 18. مهمة الطالب (Student Tasks)
  // ==========================================
  getStudentTasks: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<AcademyTask>> => {
    try {
      const { data } = await apiClient.get("/academy/student/tasks", {
        params: { skip, limit },
      });
      return data as PaginatedResponse<AcademyTask>;
    } catch (error) {
      throw handleError(error, "فشل جلب تكليفات الطالب");
    }
  },

  // ==========================================
  // 19. رفع الملفات (Upload)
  // ==========================================
  uploadFile: async (file: File): Promise<string> => {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await apiClient.post("/academy/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data.file_url;
    } catch (error) {
      throw handleError(error, "فشل رفع الملف");
    }
  },

  // ==========================================
  // 20. المستأجر (Tenant)
  // ==========================================
  getTenantByDomain: async (domain: string): Promise<any> => {
    try {
      const { data } = await apiClient.get("/academy/tenants/by-domain", {
        params: { domain },
      });
      return data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw handleError(error, "فشل جلب بيانات المستأجر");
    }
  },

  createTenant: async (payload: any): Promise<any> => {
    try {
      const { data } = await apiClient.post("/academy/tenants", payload);
      return data;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المستأجر");
    }
  },

  // ==========================================
  // 21. كورسات الطالب (My Courses)
  // ==========================================
  getMyCourses: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Course>> => {
    try {
      const { data } = await apiClient.get("/academy/student/my-courses", {
        params: { skip, limit },
      });
      return data as PaginatedResponse<Course>;
    } catch (error) {
      throw handleError(error, "فشل جلب كورساتي");
    }
  },

  // ==========================================
  // 22. الشارات (Badges)
  // ==========================================
  getBadges: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Badge>> => {
    try {
      const tenantId = getTenantId();
      const { data } = await apiClient.get("/academy/student/badges", {
        params: { tenant_id: tenantId, skip, limit },
      });
      return data as PaginatedResponse<Badge>;
    } catch (error) {
      throw handleError(error, "فشل جلب الشارات");
    }
  },
};