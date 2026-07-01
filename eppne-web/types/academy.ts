// types/academy.ts

// ==========================================
// 1. الأنواع الأساسية (Core Types)
// ==========================================

export interface Course {
  id: number;
  tenant_id: number;
  org_entity_id: number;
  track_id?: number;
  bootcamp_id?: number;
  instructor_id?: number;
  title: string;
  description?: string;
  thumbnail_url?: string;
  price_mrusdt: number;
  currency: string;
  level: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED';
  is_free: boolean;
  is_published: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CourseUnit {
  id: number;
  course_id: number;
  title: string;
  description?: string;
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeNode {
  id: number;
  course_id: number;
  unit_id?: number;
  title: string;
  description?: string;
  content_type: 'VIDEO' | 'ARTICLE' | 'QUIZ' | 'LIVE' | 'SIMULATION' | 'MATERIAL' | 'TASK';
  content_url?: string;
  is_free_preview: boolean;
  is_mandatory: boolean;
  order_index: number;
  reward_currency?: string;
  reward_amount: number;
  created_at: string;
  updated_at: string;
}

export interface AcademyTask {
  id: number;
  course_id: number;
  cohort_id?: number;
  title: string;
  description: string;
  deadline?: string;
  max_score: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ==========================================
// 2. الاشتراكات والتسليمات (Enrollments & Submissions)
// ==========================================

export interface Enrollment {
  id: number;
  user_id: number;
  course_id: number;
  cohort_id?: number;
  payment_method: string;
  payment_status: string;
  payment_ref?: string;
  paid_amount: number;
  status: string;
  progress_percentage: number;
  is_completed: boolean;
  last_accessed?: string;
  created_at: string;
  updated_at: string;
  course?: Course;
}

export interface TaskSubmission {
  id: number;
  task_id: number;
  user_id: number;
  file_url?: string;
  student_notes?: string;
  grade?: number;
  instructor_feedback?: string;
  status: 'SUBMITTED' | 'GRADED' | 'REJECTED';
  submitted_at: string;
  updated_at: string;
  user?: {
    id: number;
    username: string;
    email: string;
  };
}

// ==========================================
// 3. المعسكرات والمسارات والدفعات (Bootcamps, Tracks, Cohorts)
// ==========================================

export interface Bootcamp {
  id: number;
  org_entity_id: number;
  title: string;
  description?: string;
  duration_days: number;
  target_rank?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Track {
  id: number;
  bootcamp_id?: number;
  org_entity_id: number;
  title: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Cohort {
  id: number;
  org_entity_id: number;
  name: string;
  start_date?: string;
  end_date?: string;
  max_capacity?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ==========================================
// 4. الكيانات التنظيمية (Organization Entities)
// ==========================================

export interface OrganizationEntity {
  id: number;
  tenant_id: number;
  parent_id?: number;
  name: string;
  entity_type: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  children?: OrganizationEntity[];
}

// ==========================================
// 5. الجلسات الحية (Live Sessions)
// ==========================================

export interface LiveSession {
  id: number;
  node_id: number;
  instructor_id: number;
  cohort_id?: number;
  title: string;
  description?: string;
  scheduled_start: string;
  scheduled_end: string;
  session_type: 'ONLINE' | 'OFFLINE' | 'HYBRID';
  location?: string;
  meeting_url?: string;
  recording_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ==========================================
// 6. الشهادات (Certificates)
// ==========================================

export interface Certificate {
  id: number;
  user_id: number;
  course_id: number;
  certificate_hash: string;
  grade: number;
  issued_at: string;
  is_revoked?: boolean;
  revoked_at?: string;
  revoked_reason?: string;
  created_at: string;
  user?: {
    id: number;
    username: string;
    email: string;
  };
  course?: {
    id: number;
    title: string;
  };
}

// ==========================================
// 7. الاختبارات (Quizzes)
// ==========================================

export interface QuizQuestion {
  id: number;
  type: 'MCQ' | 'TRUE_FALSE' | 'SHORT_ANSWER';
  text: string;
  options?: string[];
  correct_answer: string;
  points: number;
}

export interface Quiz {
  id: number;
  node_id: number;
  title: string;
  passing_score: number;
  max_attempts: number;
  time_limit_minutes?: number;
  questions: QuizQuestion[];
  created_at: string;
  updated_at: string;
}

// ==========================================
// 8. التوائم الرقمية والكاميرات (Digital Twins & Cameras)
// ==========================================

export interface DigitalTwin {
  id: number;
  user_id: number;
  learning_style: 'VISUAL' | 'AUDITORY' | 'KINESTHETIC' | 'ADAPTIVE';
  cognitive_map?: {
    strengths: string;
    weak_areas: string;
  };
  ai_recommendations?: string[];
  created_at: string;
  updated_at: string;
}

export interface CameraAnalysis {
  id: number;
  org_entity_id: number;
  session_id?: number;
  camera_device_id: string;
  timestamp: string;
  detected_faces_count: number;
  attention_score?: number;
  emotions_summary?: Record<string, number>;
  active_speaker_id?: number;
  raw_analysis_log?: Record<string, any>;
  created_at: string;
}

// ==========================================
// 9. إحصائيات المدرب (Instructor Stats)
// ==========================================

export interface InstructorStats {
  total_students: number;
  total_courses: number;
  pending_submissions: number;
  total_certificates: number;
  avg_rating?: number;
  total_revenue?: number;
}

export interface GradingStats {
  pending_tasks: number;
  avg_grading_time: string;
  total_graded: number;
  completion_rate: number;
}

// ==========================================
// 10. دعم Pagination (معيار لجميع نقاط النهاية)
// ==========================================

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  skip: number;
  limit: number;
}

// ==========================================
// 11. مخططات الإرسال (Payloads) للـ Mutations
// ==========================================

export interface EnrollmentPayload {
  cohort_id?: number;
  payment_method: 'WALLET' | 'AGENT' | 'VISA' | 'FREE';
  payment_ref?: string;
  affiliate_code?: string; // ✅ إضافة حقل كود الإحالة
}

export interface ProgressUpdatePayload {
  progress_percentage: number;
}

export interface TaskSubmissionPayload {
  file_url?: string;
  student_notes?: string;
}

export interface TaskGradePayload {
  grade: number;
  instructor_feedback: string;
  status: 'GRADED' | 'REJECTED';
}

// ==========================================
// 12. أنواع إضافية للـ Leaderboard
// ==========================================

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  total_xp: number;
  username?: string;
}

// ==========================================
// 13. الشارات (Badges)
// ==========================================

export interface Badge {
  id: number;
  user_id: number;
  badge_type: 'GOLD' | 'SILVER' | 'BRONZE' | 'PLATINUM' | 'CUSTOM';
  title: string;
  description?: string;
  xp_reward: number;
  unlocked_at: string;
  created_at: string;
}