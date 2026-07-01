// hooks/academy-queries.ts
import {
  useQuery,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { AcademyService } from "@/services/academy.service";
import {
  Course,
  Enrollment,
  TaskSubmission,
  OrganizationEntity,
  LiveSession,
  Certificate,
  DigitalTwin,
  CameraAnalysis,
  Quiz,
  AcademyTask,
  Cohort,
  Bootcamp,
  Track,
  CourseUnit,
  KnowledgeNode,
  Badge,
  EnrollmentPayload,
  ProgressUpdatePayload,
  TaskSubmissionPayload,
  TaskGradePayload,
} from "@/types/academy";

// ==========================================
// 1. الكورسات (Courses)
// ==========================================
export const useCourses = (limit: number = 20) => {
  return useInfiniteQuery({
    queryKey: ["academy", "courses", "infinite"],
    queryFn: ({ pageParam = 0 }) =>
      AcademyService.getCourses(pageParam, limit),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.reduce((acc, page) => acc + page.data.length, 0);
      return totalFetched < lastPage.total ? totalFetched : undefined;
    },
    staleTime: 5 * 60 * 1000,
  });
};

export const useStoreCourses = (limit: number = 20) => {
  return useInfiniteQuery({
    queryKey: ["academy", "store", "courses"],
    queryFn: ({ pageParam = 0 }) =>
      AcademyService.getStoreCourses(pageParam, limit),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.reduce((acc, page) => acc + page.data.length, 0);
      return totalFetched < lastPage.total ? totalFetched : undefined;
    },
    staleTime: 2 * 60 * 1000,
  });
};

export const useCourse = (courseId: number) => {
  return useQuery({
    queryKey: ["academy", "course", courseId],
    queryFn: () => AcademyService.getCourseById(courseId),
    enabled: !!courseId,
    staleTime: 10 * 60 * 1000,
  });
};

export const useCreateCourse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => AcademyService.createCourse(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "courses"] });
      queryClient.invalidateQueries({ queryKey: ["academy", "store", "courses"] });
    },
  });
};

export const useUpdateCourse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ courseId, data }: { courseId: number; data: any }) =>
      AcademyService.updateCourse(courseId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["academy", "course", variables.courseId] });
      queryClient.invalidateQueries({ queryKey: ["academy", "courses"] });
    },
  });
};

export const useDeleteCourse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (courseId: number) => AcademyService.deleteCourse(courseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "courses"] });
    },
  });
};

// ==========================================
// 2. المنهج (Curriculum)
// ==========================================
export const useCurriculum = (courseId: number) => {
  return useQuery({
    queryKey: ["academy", "curriculum", courseId],
    queryFn: () => AcademyService.getCurriculum(courseId),
    enabled: !!courseId,
    staleTime: 15 * 60 * 1000,
  });
};

// ==========================================
// 3. الوحدات (Units)
// ==========================================
export const useCreateCourseUnit = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ courseId, data }: { courseId: number; data: any }) =>
      AcademyService.createCourseUnit(courseId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "curriculum", variables.courseId],
      });
    },
  });
};

export const useUpdateCourseUnit = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, title, courseId }: { unitId: number; title: string; courseId: number }) =>
      AcademyService.updateCourseUnit(unitId, title),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "curriculum", variables.courseId],
      });
    },
  });
};

export const useDeleteCourseUnit = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, courseId }: { unitId: number; courseId: number }) =>
      AcademyService.deleteCourseUnit(unitId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "curriculum", variables.courseId],
      });
    },
  });
};

// ==========================================
// 4. الدروس (Nodes)
// ==========================================
export const useCreateKnowledgeNode = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      courseId,
      unitId,
      data,
    }: {
      courseId: number;
      unitId: number;
      data: any;
    }) => AcademyService.createKnowledgeNode(courseId, unitId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "curriculum", variables.courseId],
      });
    },
  });
};

export const useUpdateKnowledgeNode = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ nodeId, title, courseId }: { nodeId: number; title: string; courseId: number }) =>
      AcademyService.updateKnowledgeNode(nodeId, title),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "curriculum", variables.courseId],
      });
    },
  });
};

export const useDeleteKnowledgeNode = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ nodeId, courseId }: { nodeId: number; courseId: number }) =>
      AcademyService.deleteKnowledgeNode(nodeId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "curriculum", variables.courseId],
      });
    },
  });
};

// ==========================================
// 5. مواد الدروس (Materials)
// ==========================================
export const useCreateNodeMaterial = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ nodeId, data }: { nodeId: number; data: any }) =>
      AcademyService.createNodeMaterial(nodeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "curriculum"] });
    },
  });
};

// ==========================================
// 6. الاختبارات (Quizzes)
// ==========================================
export const useCreateQuiz = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ nodeId, data }: { nodeId: number; data: any }) =>
      AcademyService.createQuiz(nodeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "curriculum"] });
    },
  });
};

export const useQuizResults = (quizId: number) => {
  return useQuery({
    queryKey: ["academy", "quiz-results", quizId],
    queryFn: () => AcademyService.getQuizResults(quizId),
    enabled: !!quizId,
    staleTime: 5 * 60 * 1000,
  });
};

// ==========================================
// 7. التكليفات (Tasks)
// ==========================================
export const useTasks = (courseId: number, skip: number = 0, limit: number = 20) => {
  return useQuery({
    queryKey: ["academy", "tasks", courseId, skip, limit],
    queryFn: () => AcademyService.getTasks(courseId, skip, limit),
    enabled: !!courseId,
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreateTask = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => AcademyService.createTask(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "tasks", variables.course_id],
      });
    },
  });
};

// ==========================================
// 8. اشتراكات الطالب (Enrollments)
// ==========================================
export const useMyEnrollments = (limit: number = 20) => {
  return useInfiniteQuery({
    queryKey: ["academy", "my-enrollments"],
    queryFn: ({ pageParam = 0 }) =>
      AcademyService.getMyEnrollments(pageParam, limit),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.reduce((acc, page) => acc + page.data.length, 0);
      return totalFetched < lastPage.total ? totalFetched : undefined;
    },
    staleTime: 2 * 60 * 1000,
  });
};

export const useEnrollMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      courseId,
      payload,
    }: {
      courseId: number;
      payload: EnrollmentPayload;
    }) => AcademyService.enrollInCourse(courseId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["academy", "store", "courses"] });
      queryClient.invalidateQueries({ queryKey: ["academy", "my-enrollments"] });
      queryClient.invalidateQueries({
        queryKey: ["academy", "course", variables.courseId],
      });
    },
  });
};

export const useProgressMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      courseId,
      payload,
    }: {
      courseId: number;
      payload: ProgressUpdatePayload;
    }) => AcademyService.updateProgress(courseId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "my-enrollments"],
      });
      queryClient.invalidateQueries({
        queryKey: ["academy", "course", variables.courseId],
      });
    },
  });
};

// ==========================================
// 9. تسليمات التكليفات (Submissions)
// ==========================================
export const useMySubmissions = (skip: number = 0, limit: number = 20) => {
  return useQuery({
    queryKey: ["academy", "my-submissions", skip, limit],
    queryFn: () => AcademyService.getMySubmissions(skip, limit),
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubmitTaskMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskId,
      payload,
    }: {
      taskId: number;
      payload: TaskSubmissionPayload;
    }) => AcademyService.submitTask(taskId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "my-submissions"],
      });
      queryClient.invalidateQueries({
        queryKey: ["academy", "tasks", variables.taskId],
      });
    },
  });
};

export const useGradeSubmissionMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      submissionId,
      payload,
    }: {
      submissionId: number;
      payload: TaskGradePayload;
    }) => AcademyService.gradeSubmission(submissionId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "instructor", "submissions"],
      });
      queryClient.invalidateQueries({
        queryKey: ["academy", "my-submissions"],
      });
    },
  });
};

// ==========================================
// 10. لوحة الشرف (Leaderboard)
// ==========================================
export const useLeaderboard = (limit: number = 50) => {
  return useQuery({
    queryKey: ["academy", "leaderboard", limit],
    queryFn: () => AcademyService.getLeaderboard(limit),
    staleTime: 5 * 60 * 1000,
  });
};

// ==========================================
// 11. المعسكرات والمسارات (Bootcamps & Tracks)
// ==========================================
export const useBootcamps = (
  orgEntityId?: number,
  skip: number = 0,
  limit: number = 20,
  enabled: boolean = true
) => {
  return useQuery({
    queryKey: ["academy", "bootcamps", orgEntityId, skip, limit],
    queryFn: () => AcademyService.getBootcamps(orgEntityId, skip, limit),
    enabled: enabled,
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreateBootcamp = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => AcademyService.createBootcamp(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "bootcamps"] });
    },
  });
};

export const useTracks = (
  orgEntityId?: number,
  bootcampId?: number,
  skip: number = 0,
  limit: number = 20,
  enabled: boolean = true
) => {
  return useQuery({
    queryKey: ["academy", "tracks", orgEntityId, bootcampId, skip, limit],
    queryFn: () => AcademyService.getTracks(orgEntityId, bootcampId, skip, limit),
    enabled: enabled,
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreateTrack = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => AcademyService.createTrack(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "tracks"] });
    },
  });
};

// ==========================================
// 12. الدفعات (Cohorts)
// ==========================================
export const useCohorts = (
  orgEntityId: number,
  skip: number = 0,
  limit: number = 20,
  enabled: boolean = true
) => {
  return useQuery({
    queryKey: ["academy", "cohorts", orgEntityId, skip, limit],
    queryFn: () => AcademyService.getCohorts(orgEntityId, skip, limit),
    enabled: enabled,
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreateCohort = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => AcademyService.createCohort(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "cohorts", variables.org_entity_id],
      });
    },
  });
};

// ==========================================
// 13. الكيانات التنظيمية (Organization Entities)
// ==========================================
export const useOrganizationEntities = (
  skip: number = 0,
  limit: number = 100
) => {
  return useQuery({
    queryKey: ["academy", "organization-entities", skip, limit],
    queryFn: () => AcademyService.getOrganizationEntities(skip, limit),
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreateOrganizationEntity = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => AcademyService.createOrganizationEntity(data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "organization-entities"],
      });
    },
  });
};

export const useUpdateOrganizationEntity = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ entityId, data }: { entityId: number; data: any }) =>
      AcademyService.updateOrganizationEntity(entityId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "organization-entities"],
      });
    },
  });
};

export const useDeleteOrganizationEntity = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entityId: number) =>
      AcademyService.deleteOrganizationEntity(entityId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["academy", "organization-entities"],
      });
    },
  });
};

// ==========================================
// 14. الجلسات الحية (Live Sessions)
// ==========================================
export const useLiveSessions = (
  orgEntityId?: number,
  skip: number = 0,
  limit: number = 20,
  refetchInterval: number = 0
) => {
  return useQuery({
    queryKey: ["academy", "live-sessions", orgEntityId, skip, limit],
    queryFn: () => AcademyService.getLiveSessions(orgEntityId, skip, limit),
    enabled: !!orgEntityId,
    staleTime: 2 * 60 * 1000,
    refetchInterval: refetchInterval || undefined,
  });
};

export const useCreateLiveSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => AcademyService.createLiveSession(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "live-sessions"] });
    },
  });
};

export const useUpdateLiveSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: number; data: any }) =>
      AcademyService.updateLiveSession(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "live-sessions"] });
    },
  });
};

export const useDeleteLiveSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: number) =>
      AcademyService.deleteLiveSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "live-sessions"] });
    },
  });
};

// ==========================================
// 15. الشهادات (Certificates)
// ==========================================
export const useCertificates = (
  orgEntityId?: number,
  skip: number = 0,
  limit: number = 20
) => {
  return useQuery({
    queryKey: ["academy", "certificates", orgEntityId, skip, limit],
    queryFn: () => AcademyService.getCertificates(orgEntityId, skip, limit),
    enabled: !!orgEntityId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useMyCertificates = (skip: number = 0, limit: number = 20) => {
  return useQuery({
    queryKey: ["academy", "my-certificates", skip, limit],
    queryFn: () => AcademyService.getMyCertificates(skip, limit),
    staleTime: 5 * 60 * 1000,
  });
};

export const useRevokeCertificate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (certificateId: number) =>
      AcademyService.revokeCertificate(certificateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "certificates"] });
    },
  });
};

export const useReissueCertificate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (certificateId: number) =>
      AcademyService.reissueCertificate(certificateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "certificates"] });
    },
  });
};

// ==========================================
// 16. التوائم الرقمية والكاميرات
// ==========================================
export const useDigitalTwin = () => {
  return useQuery({
    queryKey: ["academy", "digital-twin"],
    queryFn: () => AcademyService.getDigitalTwin(),
    staleTime: 5 * 60 * 1000,
  });
};

export const useDigitalTwins = (skip: number = 0, limit: number = 50) => {
  return useQuery({
    queryKey: ["academy", "digital-twins", skip, limit],
    queryFn: () => AcademyService.getDigitalTwins(skip, limit),
    staleTime: 5 * 60 * 1000,
  });
};

export const useCameraAnalytics = (
  orgEntityId: number,
  skip: number = 0,
  limit: number = 20
) => {
  return useQuery({
    queryKey: ["academy", "camera-analytics", orgEntityId, skip, limit],
    queryFn: () => AcademyService.getCameraAnalytics(orgEntityId, skip, limit),
    enabled: !!orgEntityId,
    staleTime: 2 * 60 * 1000,
    refetchInterval: 30000,
  });
};

// ==========================================
// 17. إحصائيات المدرب (Instructor Stats)
// ==========================================
export const useInstructorStats = () => {
  return useQuery({
    queryKey: ["academy", "instructor", "stats"],
    queryFn: () => AcademyService.getInstructorStats(),
    staleTime: 2 * 60 * 1000,
  });
};

export const useGradingStats = () => {
  return useQuery({
    queryKey: ["academy", "instructor", "grading-stats"],
    queryFn: () => AcademyService.getGradingStats(),
    staleTime: 2 * 60 * 1000,
  });
};

export const useInstructorCourses = (skip: number = 0, limit: number = 20) => {
  return useQuery({
    queryKey: ["academy", "instructor", "courses", skip, limit],
    queryFn: () => AcademyService.getInstructorCourses(skip, limit),
    staleTime: 5 * 60 * 1000,
  });
};

// ==========================================
// 18. مهمة الطالب (Student Tasks)
// ==========================================
export const useStudentTasks = (skip: number = 0, limit: number = 20) => {
  return useQuery({
    queryKey: ["academy", "student", "tasks", skip, limit],
    queryFn: () => AcademyService.getStudentTasks(skip, limit),
    staleTime: 2 * 60 * 1000,
  });
};

// ==========================================
// 19. رفع الملفات (Upload)
// ==========================================
export const useUploadFile = () => {
  return useMutation({
    mutationFn: (file: File) => AcademyService.uploadFile(file),
  });
};

// ==========================================
// 20. المستأجر (Tenant)
// ==========================================
export const useTenantByDomain = (domain: string) => {
  return useQuery({
    queryKey: ["academy", "tenant", domain],
    queryFn: () => AcademyService.getTenantByDomain(domain),
    enabled: !!domain,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
};

export const useCreateTenant = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: any) => AcademyService.createTenant(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academy", "tenant"] });
    },
  });
};

// ==========================================
// 21. كورسات الطالب (My Courses)
// ==========================================
export const useMyCourses = (skip: number = 0, limit: number = 20) => {
  return useQuery({
    queryKey: ["academy", "my-courses", skip, limit],
    queryFn: () => AcademyService.getMyCourses(skip, limit),
    staleTime: 2 * 60 * 1000,
  });
};

// ==========================================
// 22. الشارات (Badges)
// ==========================================
export const useBadges = (skip: number = 0, limit: number = 20) => {
  return useQuery({
    queryKey: ["academy", "badges", skip, limit],
    queryFn: () => AcademyService.getBadges(skip, limit),
    staleTime: 5 * 60 * 1000,
  });
};