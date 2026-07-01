// app/(dashboard)/academy/admin/studio/page.tsx
"use client";

import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

// ✅ استبدال المتاجر القديمة بالهوكات الجديدة
import {
  useCourse,
  useCurriculum,
  useOrganizationEntities,
  useBootcamps,
  useTracks,
  useCreateCourse,
  useUpdateCourse,
  useCreateCourseUnit,
  useUpdateCourseUnit,
  useDeleteCourseUnit,
  useCreateKnowledgeNode,
  useUpdateKnowledgeNode,
  useDeleteKnowledgeNode,
  useCreateNodeMaterial,
  useCreateQuiz,
  useUploadFile,
} from "@/hooks/academy-queries";
import { AcademyService } from "@/services/academy.service";
import {
  Course,
  CourseUnit,
  KnowledgeNode,
  OrganizationEntity,
  Bootcamp,
  Track,
  Quiz,
  QuizQuestion,
} from "@/types/academy";
import { handleError } from "@/lib/error-handler";
import { getTenantId } from "@/lib/auth-utils";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Save,
  Settings,
  BookOpen,
  Cloud,
  BrainCircuit,
  Network,
  Plus,
  Layers,
  Tent,
  Route,
  Video,
  Trash2,
  Edit2,
  GripVertical,
  Check,
  X,
  Target,
  Loader2,
  HelpCircle,
  AlertCircle,
} from "lucide-react";

// ==========================================
// 🟢 مكونات فرعية محسّنة (مقسمة لتحسين الصيانة)
// ==========================================

// --- 1. مكون المعلومات الأساسية للكورس ---
function CourseBasicInfo({
  courseData,
  setCourseData,
  orgEntities,
  isOrgsLoading,
  bootcamps,
  tracks,
  courseThumbnailFile,
  setCourseThumbnailFile,
  createdCourseId,
}: any) {
  return (
    <div className="flex flex-col gap-8 w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full">
        <div className="flex flex-col gap-3 w-full">
          <Label className="text-xl font-bold">عنوان الكورس</Label>
          <Input
            placeholder="مثال: هندسة العقود الذكية"
            className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-primary shadow-inner text-lg"
            value={courseData.title}
            onChange={(e) => setCourseData({ ...courseData, title: e.target.value })}
          />
        </div>
        <div className="flex flex-col gap-3 w-full">
          <Label className="text-xl font-bold flex items-center gap-2">
            <Network className="h-5 w-5 text-primary" /> الكيان التنظيمي
          </Label>
          {isOrgsLoading ? (
            <Skeleton className="h-14 w-full rounded-xl" />
          ) : (
            <select
              className="h-14 px-4 rounded-xl bg-background/50 border-white/10 focus:border-primary focus:ring-1 outline-none shadow-inner text-lg cursor-pointer"
              value={courseData.org_entity_id}
              onChange={(e) =>
                setCourseData({ ...courseData, org_entity_id: e.target.value })
              }
            >
              <option value="" disabled>
                اختر الكلية أو القسم...
              </option>
              {orgEntities.map((entity: OrganizationEntity) => (
                <option key={entity.id} value={entity.id}>
                  {entity.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {courseData.org_entity_id && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full animate-in fade-in duration-500">
          <div className="flex flex-col gap-3 w-full">
            <Label className="text-xl font-bold flex items-center gap-2">
              <Tent className="h-5 w-5 text-primary" /> المعسكر (اختياري)
            </Label>
            <select
              className="h-14 px-4 rounded-xl bg-background/50 border-white/10 shadow-inner text-lg"
              value={courseData.bootcamp_id}
              onChange={(e) =>
                setCourseData({
                  ...courseData,
                  bootcamp_id: e.target.value,
                  track_id: "",
                })
              }
            >
              <option value="">-- كورس حر --</option>
              {bootcamps.map((bc: Bootcamp) => (
                <option key={bc.id} value={bc.id}>
                  {bc.title}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-3 w-full">
            <Label className="text-xl font-bold flex items-center gap-2">
              <Route className="h-5 w-5 text-primary" /> المسار (اختياري)
            </Label>
            <select
              className="h-14 px-4 rounded-xl bg-background/50 border-white/10 shadow-inner text-lg"
              value={courseData.track_id}
              onChange={(e) =>
                setCourseData({ ...courseData, track_id: e.target.value })
              }
            >
              <option value="">-- كورس حر --</option>
              {tracks.map((tr: Track) => (
                <option key={tr.id} value={tr.id}>
                  {tr.title}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full">
        <div className="flex flex-col gap-3 w-full">
          <Label className="text-xl font-bold">الاستثمار (MR_USDT)</Label>
          <Input
            type="number"
            min="0"
            step="0.01"
            placeholder="50"
            className="h-14 rounded-xl bg-background/50 border-white/10 shadow-inner font-mono text-lg"
            value={courseData.price_mrusdt}
            onChange={(e) =>
              setCourseData({ ...courseData, price_mrusdt: e.target.value })
            }
          />
        </div>
        <div className="flex flex-col gap-3 w-full">
          <Label className="text-xl font-bold">المستوى</Label>
          <select
            className="h-14 px-4 rounded-xl bg-background/50 border-white/10 shadow-inner text-lg"
            value={courseData.level}
            onChange={(e) =>
              setCourseData({ ...courseData, level: e.target.value })
            }
          >
            <option value="BEGINNER">تأسيسي (مبتدئ)</option>
            <option value="INTERMEDIATE">تطبيقي (متوسط)</option>
            <option value="ADVANCED">احترافي (متقدم)</option>
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-3 w-full">
        <Label className="text-xl font-bold">صورة الغلاف (Thumbnail)</Label>
        <Input
          type="file"
          accept="image/*"
          onChange={(e) => setCourseThumbnailFile(e.target.files?.[0] || null)}
          className="h-14 bg-background/50 border-white/10 rounded-xl pt-3 cursor-pointer"
        />
        {courseData.thumbnail_url && !courseThumbnailFile && (
          <span className="text-sm text-emerald-500 font-bold px-2">
            ✓ تم رفع صورة مسبقاً.
          </span>
        )}
      </div>

      <div className="flex flex-col gap-3 w-full">
        <Label className="text-xl font-bold">الوصف المعرفي</Label>
        <textarea
          rows={5}
          placeholder="اشرح مخرجات التعلم..."
          className="w-full p-5 text-lg bg-background/50 border-white/10 rounded-2xl outline-none shadow-inner"
          value={courseData.description}
          onChange={(e) =>
            setCourseData({ ...courseData, description: e.target.value })
          }
        />
      </div>
    </div>
  );
}

// --- 2. مكون بناء المنهج (Curriculum Builder) ---
function CurriculumBuilder({
  createdCourseId,
  localUnits,
  setLocalUnits,
  localNodes,
  setLocalNodes,
  isCurriculumLoading,
  mutations,
  handleDragEnd,
  editingUnitId,
  setEditingUnitId,
  editUnitTitle,
  setEditUnitTitle,
  editingNodeId,
  setEditingNodeId,
  editNodeTitle,
  setEditNodeTitle,
  setIsUnitModalOpen,
  setIsNodeModalOpen,
  setSelectedUnitIdForNode,
  setIsMaterialModalOpen,
  setSelectedNodeIdForMaterial,
  setIsQuizModalOpen,
  setSelectedNodeIdForQuiz,
}: any) {
  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card className="w-full border-white/10 bg-card/40 backdrop-blur-2xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-8 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-black flex items-center gap-3">
              <Layers className="h-8 w-8 text-primary" /> المنهج الدراسي
            </h2>
          </div>
          <Button
            onClick={() => setIsUnitModalOpen(true)}
            size="lg"
            className="h-14 px-6 text-lg rounded-2xl shadow-xl"
          >
            <Plus className="ml-2 h-6 w-6" /> إضافة وحدة
          </Button>
        </CardContent>
      </Card>

      {isCurriculumLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-[2rem]" />
          <Skeleton className="h-32 w-full rounded-[2rem]" />
        </div>
      ) : (
        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId="units-list" type="UNIT">
            {(provided) => (
              <div {...provided.droppableProps} ref={provided.innerRef} className="space-y-6">
                {localUnits.map((unit: CourseUnit, index: number) => (
                  <Draggable
                    key={unit.id.toString()}
                    draggableId={`unit-${unit.id}`}
                    index={index}
                  >
                    {(provided) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        style={provided.draggableProps.style as React.CSSProperties}
                      >
                        <Card className="w-full border-white/10 bg-card/60 backdrop-blur-md rounded-[2rem] shadow-sm hover:border-primary/30 transition-colors">
                          <CardContent className="p-6">
                            <div className="flex items-center justify-between border-b border-border/50 pb-4 mb-4">
                              <div className="flex items-center gap-3 w-full max-w-lg">
                                <div
                                  {...provided.dragHandleProps}
                                  className="text-muted-foreground hover:text-primary cursor-grab p-1"
                                >
                                  <GripVertical className="h-6 w-6" />
                                </div>
                                {editingUnitId === unit.id ? (
                                  <div className="flex items-center gap-2 w-full">
                                    <Input
                                      value={editUnitTitle}
                                      onChange={(e) => setEditUnitTitle(e.target.value)}
                                      className="h-10 bg-background/50 border-white/10"
                                      autoFocus
                                    />
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      className="text-emerald-500"
                                      onClick={() => {
                                        mutations.updateUnit.mutate({
                                          unitId: unit.id,
                                          title: editUnitTitle,
                                        });
                                        setEditingUnitId(null);
                                      }}
                                    >
                                      <Check className="h-5 w-5" />
                                    </Button>
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      className="text-red-500"
                                      onClick={() => setEditingUnitId(null)}
                                    >
                                      <X className="h-5 w-5" />
                                    </Button>
                                  </div>
                                ) : (
                                  <h3 className="text-xl font-black text-foreground flex items-center gap-3">
                                    الوحدة {index + 1}: {unit.title}
                                    <button
                                      onClick={() => {
                                        setEditingUnitId(unit.id);
                                        setEditUnitTitle(unit.title);
                                      }}
                                      className="text-muted-foreground hover:text-primary"
                                    >
                                      <Edit2 className="h-4 w-4" />
                                    </button>
                                  </h3>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  className="rounded-xl shadow-md"
                                  onClick={() => {
                                    setSelectedUnitIdForNode(unit.id);
                                    setIsNodeModalOpen(true);
                                  }}
                                >
                                  إضافة درس
                                </Button>
                                <button
                                  onClick={() =>
                                    mutations.deleteUnit.mutate({ unitId: unit.id })
                                  }
                                  className="text-red-500 hover:bg-red-500/10 p-2 rounded-lg"
                                >
                                  <Trash2 className="w-5 h-5" />
                                </button>
                              </div>
                            </div>

                            <Droppable droppableId={`nodes-${unit.id}`} type="NODE">
                              {(provided) => (
                                <div
                                  {...provided.droppableProps}
                                  ref={provided.innerRef}
                                  className="space-y-3 pl-4 border-r-2 border-primary/20 ml-2 min-h-[50px]"
                                >
                                  {localNodes
                                    .filter((n: KnowledgeNode) => n.unit_id === unit.id)
                                    .map((node: KnowledgeNode, nodeIndex: number) => (
                                      <Draggable
                                        key={node.id.toString()}
                                        draggableId={`node-${node.id}`}
                                        index={nodeIndex}
                                      >
                                        {(provided) => (
                                          <div
                                            ref={provided.innerRef}
                                            {...provided.draggableProps}
                                            style={
                                              provided.draggableProps
                                                .style as React.CSSProperties
                                            }
                                            className="flex items-center justify-between bg-background/40 p-4 rounded-xl border border-white/5 hover:bg-background/60 transition-colors group"
                                          >
                                            <div className="flex items-center gap-3">
                                              <div
                                                {...provided.dragHandleProps}
                                                className="text-muted-foreground hover:text-primary cursor-grab"
                                              >
                                                <GripVertical className="h-5 w-5" />
                                              </div>
                                              {editingNodeId === node.id ? (
                                                <div className="flex items-center gap-2 w-full max-w-sm">
                                                  <Input
                                                    value={editNodeTitle}
                                                    onChange={(e) =>
                                                      setEditNodeTitle(e.target.value)
                                                    }
                                                    className="h-8 bg-background/50 border-white/10"
                                                  />
                                                  <button
                                                    onClick={() => {
                                                      mutations.updateNode.mutate({
                                                        nodeId: node.id,
                                                        title: editNodeTitle,
                                                      });
                                                      setEditingNodeId(null);
                                                    }}
                                                    className="text-emerald-500 p-1"
                                                  >
                                                    <Check className="h-4 w-4" />
                                                  </button>
                                                  <button
                                                    onClick={() =>
                                                      setEditingNodeId(null)
                                                    }
                                                    className="text-red-500 p-1"
                                                  >
                                                    <X className="h-4 w-4" />
                                                  </button>
                                                </div>
                                              ) : (
                                                <div className="flex items-center gap-2">
                                                  <span className="font-bold text-lg">
                                                    {node.title}
                                                  </span>
                                                  {node.content_type === "LIVE" && (
                                                    <span className="text-xs bg-blue-500/10 text-blue-500 px-2 py-1 rounded border border-blue-500/20 font-bold">
                                                      بث مباشر
                                                    </span>
                                                  )}
                                                  {node.content_type === "TASK" && (
                                                    <span className="text-xs bg-orange-500/10 text-orange-500 px-2 py-1 rounded border border-orange-500/20 font-bold">
                                                      تكليف
                                                    </span>
                                                  )}
                                                  {node.content_type === "QUIZ" && (
                                                    <span className="text-xs bg-emerald-500/10 text-emerald-500 px-2 py-1 rounded border border-emerald-500/20 font-bold">
                                                      اختبار
                                                    </span>
                                                  )}
                                                  <button
                                                    onClick={() => {
                                                      setEditingNodeId(node.id);
                                                      setEditNodeTitle(node.title);
                                                    }}
                                                    className="text-muted-foreground hover:text-primary p-1"
                                                  >
                                                    <Edit2 className="h-4 w-4" />
                                                  </button>
                                                </div>
                                              )}
                                            </div>
                                            <div className="flex gap-2">
                                              <button
                                                onClick={() =>
                                                  mutations.deleteNode.mutate({
                                                    nodeId: node.id,
                                                  })
                                                }
                                                className="text-red-500 hover:bg-red-500/10 p-1.5 rounded-lg opacity-0 group-hover:opacity-100"
                                              >
                                                <Trash2 className="w-4 h-4" />
                                              </button>
                                              <Button
                                                size="sm"
                                                variant="outline"
                                                className="border-primary/20 bg-background/50"
                                                onClick={() => {
                                                  setSelectedNodeIdForMaterial(node.id);
                                                  setIsMaterialModalOpen(true);
                                                }}
                                              >
                                                إضافة محتوى
                                              </Button>
                                              {node.content_type === "QUIZ" && (
                                                <Button
                                                  size="sm"
                                                  className="bg-emerald-500 hover:bg-emerald-600 text-white"
                                                  onClick={() => {
                                                    setSelectedNodeIdForQuiz(node.id);
                                                    setIsQuizModalOpen(true);
                                                  }}
                                                >
                                                  بناء الاختبار
                                                </Button>
                                              )}
                                            </div>
                                          </div>
                                        )}
                                      </Draggable>
                                    ))}
                                  {provided.placeholder}
                                </div>
                              )}
                            </Droppable>
                          </CardContent>
                        </Card>
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        </DragDropContext>
      )}
    </div>
  );
}

// ==========================================
// 🟢 الصفحة الرئيسية (محسّنة)
// ==========================================
export default function AcademyStudioPage() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const courseIdParam = searchParams.get("courseId");
  const tenantId = useMemo(() => getTenantId(), []);

  // --- حالة الواجهة ---
  const [activeTab, setActiveTab] = useState("basic");
  const [createdCourseId, setCreatedCourseId] = useState<number | null>(
    courseIdParam ? Number(courseIdParam) : null
  );

  // --- حالات التعديل ---
  const [editingUnitId, setEditingUnitId] = useState<number | null>(null);
  const [editUnitTitle, setEditUnitTitle] = useState("");
  const [editingNodeId, setEditingNodeId] = useState<number | null>(null);
  const [editNodeTitle, setEditNodeTitle] = useState("");

  // --- حالات البيانات ---
  const [courseData, setCourseData] = useState({
    title: "",
    price_mrusdt: "",
    level: "BEGINNER",
    description: "",
    org_entity_id: "",
    bootcamp_id: "",
    track_id: "",
    thumbnail_url: "",
  });
  const [courseThumbnailFile, setCourseThumbnailFile] = useState<File | null>(null);

  // --- حالة المنهج المحلية (Optimistic UI) ---
  const [localUnits, setLocalUnits] = useState<CourseUnit[]>([]);
  const [localNodes, setLocalNodes] = useState<KnowledgeNode[]>([]);

  // --- حالة النوافذ المنبثقة ---
  const [isUnitModalOpen, setIsUnitModalOpen] = useState(false);
  const [unitData, setUnitData] = useState({ title: "", description: "" });

  const [isNodeModalOpen, setIsNodeModalOpen] = useState(false);
  const [selectedUnitIdForNode, setSelectedUnitIdForNode] = useState<number | null>(
    null
  );
  const [nodeData, setNodeData] = useState<any>({
    title: "",
    content_type: "MATERIAL",
    reward_amount: "",
    reward_currency: "XP",
    scheduled_start: "",
    meeting_url: "",
  });

  const [isMaterialModalOpen, setIsMaterialModalOpen] = useState(false);
  const [selectedNodeIdForMaterial, setSelectedNodeIdForMaterial] = useState<
    number | null
  >(null);
  const [materialData, setMaterialData] = useState({
    title: "",
    material_type: "YOUTUBE",
    file_url: "",
    is_downloadable: false,
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [isQuizModalOpen, setIsQuizModalOpen] = useState(false);
  const [selectedNodeIdForQuiz, setSelectedNodeIdForQuiz] = useState<number | null>(
    null
  );
  const [quizData, setQuizData] = useState({
    title: "",
    passing_score: 70,
    max_attempts: 3,
    time_limit_minutes: 15,
    questions: [] as QuizQuestion[],
  });
  const [currentQuestion, setCurrentQuestion] = useState<QuizQuestion>({
    id: 1,
    type: "MCQ",
    text: "",
    options: ["", "", "", ""],
    correct_answer: "",
    points: 1,
  });

  // ==========================================
  // 🟢 1. جلب البيانات باستخدام الهوكات الجديدة
  // ==========================================

  // الكيانات التنظيمية
  const {
    data: orgEntitiesData,
    isLoading: isOrgsLoading,
    error: orgsError,
  } = useOrganizationEntities(0, 100);

  const orgEntities = orgEntitiesData?.data || [];

  // الكورس (إذا كان موجوداً)
  const {
    data: fetchedCourse,
    isLoading: isCourseLoading,
    error: courseError,
  } = useCourse(createdCourseId || 0, !!createdCourseId);

  // المنهج
  const {
    data: fetchedCurriculum,
    isLoading: isCurriculumLoading,
    error: curriculumError,
  } = useCurriculum(createdCourseId || 0, !!createdCourseId);

  // المعسكرات (حسب الكيان المختار)
  const {
    data: bootcampsData,
    isLoading: isBootcampsLoading,
  } = useBootcamps(
    courseData.org_entity_id ? Number(courseData.org_entity_id) : undefined,
    0,
    50,
    !!courseData.org_entity_id
  );
  const bootcamps = bootcampsData?.data || [];

  // المسارات (حسب الكيان المختار)
  const {
    data: tracksData,
    isLoading: isTracksLoading,
  } = useTracks(
    courseData.org_entity_id ? Number(courseData.org_entity_id) : undefined,
    undefined,
    0,
    50,
    !!courseData.org_entity_id
  );
  const tracks = tracksData?.data || [];

  // ==========================================
  // 🟢 2. محركات العمليات (Mutations)
  // ==========================================

  const createCourse = useCreateCourse();
  const updateCourse = useUpdateCourse();
  const createUnit = useCreateCourseUnit();
  const updateUnit = useUpdateCourseUnit();
  const deleteUnit = useDeleteCourseUnit();
  const createNode = useCreateKnowledgeNode();
  const updateNode = useUpdateKnowledgeNode();
  const deleteNode = useDeleteKnowledgeNode();
  const createMaterial = useCreateNodeMaterial();
  const createQuiz = useCreateQuiz();
  const uploadFile = useUploadFile();

  // تجميع الـ Mutations في كائن واحد للتبسيط
  const mutations = useMemo(
    () => ({
      createCourse,
      updateCourse,
      createUnit,
      updateUnit,
      deleteUnit,
      createNode,
      updateNode,
      deleteNode,
      createMaterial,
      createQuiz,
      uploadFile,
    }),
    [
      createCourse,
      updateCourse,
      createUnit,
      updateUnit,
      deleteUnit,
      createNode,
      updateNode,
      deleteNode,
      createMaterial,
      createQuiz,
      uploadFile,
    ]
  );

  // ==========================================
  // 🟢 3. تهيئة البيانات (useEffect)
  // ==========================================

  // تعيين معرف الكورس من الـ URL
  useEffect(() => {
    if (courseIdParam) {
      setCreatedCourseId(Number(courseIdParam));
      setActiveTab("curriculum");
    }
  }, [courseIdParam]);

  // تحديث بيانات الكورس عند جلبها
  useEffect(() => {
    if (fetchedCourse) {
      setCourseData({
        title: fetchedCourse.title || "",
        description: fetchedCourse.description || "",
        price_mrusdt: fetchedCourse.price_mrusdt?.toString() || "",
        level: fetchedCourse.level || "BEGINNER",
        org_entity_id: fetchedCourse.org_entity_id?.toString() || "",
        bootcamp_id: fetchedCourse.bootcamp_id?.toString() || "",
        track_id: fetchedCourse.track_id?.toString() || "",
        thumbnail_url: fetchedCourse.thumbnail_url || "",
      });
    }
  }, [fetchedCourse]);

  // تحديث المنهج المحلي
  useEffect(() => {
    if (fetchedCurriculum) {
      setLocalUnits(fetchedCurriculum.units || []);
      setLocalNodes(fetchedCurriculum.nodes || []);
    }
  }, [fetchedCurriculum]);

  // ==========================================
  // 🟢 4. معالجة الأخطاء
  // ==========================================

  if (orgsError) {
    const error = handleError(orgsError, "جلب الكيانات التنظيمية");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل البيانات</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{error.message}</p>
        <Button
          onClick={() => window.location.reload()}
          size="lg"
          className="rounded-xl h-14 px-8"
        >
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  // ==========================================
  // 🟢 5. دوال المعالجة (محسّنة بـ useCallback)
  // ==========================================

  const handleSaveCourse = useCallback(async () => {
    if (!courseData.title.trim() || !courseData.org_entity_id) {
      toast.error("بيانات غير مكتملة: العنوان والكيان التنظيمي حقول إجبارية.");
      return;
    }

    try {
      let finalThumbnailUrl = courseData.thumbnail_url;
      if (courseThumbnailFile) {
        finalThumbnailUrl = await uploadFile.mutateAsync(courseThumbnailFile);
      }

      const payload = {
        title: courseData.title,
        description: courseData.description,
        price_mrusdt: Number(courseData.price_mrusdt) || 0,
        level: courseData.level,
        tenant_id: tenantId,
        org_entity_id: Number(courseData.org_entity_id),
        bootcamp_id: courseData.bootcamp_id ? Number(courseData.bootcamp_id) : undefined,
        track_id: courseData.track_id ? Number(courseData.track_id) : undefined,
        currency: "MR_USDT",
        thumbnail_url: finalThumbnailUrl,
      };

      if (createdCourseId) {
        await updateCourse.mutateAsync({
          courseId: createdCourseId,
          data: payload,
        });
        toast.success("تم تحديث الكورس بنجاح!");
      } else {
        const newCourse = await createCourse.mutateAsync(payload);
        setCreatedCourseId(newCourse.id);
        toast.success("تم إنشاء الكورس بنجاح!");
        setActiveTab("curriculum");
      }
    } catch (error) {
      const err = handleError(error, "حفظ الكورس");
      toast.error(err.message);
    }
  }, [courseData, courseThumbnailFile, createdCourseId, tenantId, createCourse, updateCourse, uploadFile]);

  const handleSaveUnit = useCallback(() => {
    if (!unitData.title || !createdCourseId) {
      toast.error("يرجى إدخال عنوان الوحدة.");
      return;
    }
    createUnit.mutate(
      {
        courseId: createdCourseId,
        data: unitData,
      },
      {
        onSuccess: () => {
          toast.success("تم إنشاء الوحدة بنجاح!");
          setIsUnitModalOpen(false);
          setUnitData({ title: "", description: "" });
          queryClient.invalidateQueries({
            queryKey: ["academy", "curriculum", createdCourseId],
          });
        },
        onError: (error) => {
          const err = handleError(error, "إنشاء الوحدة");
          toast.error(err.message);
        },
      }
    );
  }, [unitData, createdCourseId, createUnit, queryClient]);

  const handleSaveNode = useCallback(() => {
    if (!nodeData.title || !selectedUnitIdForNode || !createdCourseId) {
      toast.error("تأكد من عنوان الدرس.");
      return;
    }
    createNode.mutate(
      {
        courseId: createdCourseId,
        unitId: selectedUnitIdForNode,
        data: nodeData,
      },
      {
        onSuccess: async (newNode) => {
          // إذا كان نوع الدرس بث مباشر، نقوم بإنشاء الجلسة
          if (nodeData.content_type === "LIVE" && nodeData.meeting_url) {
            try {
              await AcademyService.createLiveSession(newNode.id, {
                title: nodeData.title,
                scheduled_start: nodeData.scheduled_start || new Date().toISOString(),
                scheduled_end: new Date(
                  new Date(nodeData.scheduled_start || new Date()).getTime() +
                    60 * 60 * 1000
                ).toISOString(),
                meeting_url: nodeData.meeting_url,
                instructor_id: 1, // TODO: جلب من المستخدم الحالي
              });
              toast.success("تم جدولة البث المباشر بنجاح!");
            } catch (error) {
              const err = handleError(error, "جدولة البث المباشر");
              toast.error(err.message);
            }
          }
          setIsNodeModalOpen(false);
          setNodeData({
            title: "",
            content_type: "MATERIAL",
            reward_amount: "",
            reward_currency: "XP",
            scheduled_start: "",
            meeting_url: "",
          });
          queryClient.invalidateQueries({
            queryKey: ["academy", "curriculum", createdCourseId],
          });
        },
        onError: (error) => {
          const err = handleError(error, "إنشاء الدرس");
          toast.error(err.message);
        },
      }
    );
  }, [nodeData, selectedUnitIdForNode, createdCourseId, createNode, queryClient]);

  const handleSaveMaterial = useCallback(async () => {
    if (!selectedNodeIdForMaterial) return;

    let finalUrl = materialData.file_url;
    if (selectedFile && ["PDF", "DOC", "IMAGE"].includes(materialData.material_type)) {
      finalUrl = await uploadFile.mutateAsync(selectedFile);
    }
    if (!finalUrl) {
      toast.error("يرجى إدخال الرابط أو رفع الملف.");
      return;
    }

    createMaterial.mutate(
      {
        nodeId: selectedNodeIdForMaterial,
        data: { ...materialData, file_url: finalUrl },
      },
      {
        onSuccess: () => {
          toast.success("تم ربط المحتوى بنجاح!");
          setIsMaterialModalOpen(false);
          setMaterialData({
            title: "",
            material_type: "YOUTUBE",
            file_url: "",
            is_downloadable: false,
          });
          setSelectedFile(null);
          queryClient.invalidateQueries({
            queryKey: ["academy", "curriculum", createdCourseId],
          });
        },
        onError: (error) => {
          const err = handleError(error, "ربط المحتوى");
          toast.error(err.message);
        },
      }
    );
  }, [selectedNodeIdForMaterial, materialData, selectedFile, createMaterial, uploadFile, queryClient, createdCourseId]);

  const handleSaveQuiz = useCallback(() => {
    if (!selectedNodeIdForQuiz || quizData.questions.length === 0) {
      toast.error("أضف سؤالاً واحداً على الأقل.");
      return;
    }
    createQuiz.mutate(
      {
        nodeId: selectedNodeIdForQuiz,
        data: quizData,
      },
      {
        onSuccess: () => {
          toast.success("تم اعتماد الاختبار السيادي بنجاح!");
          setIsQuizModalOpen(false);
          setQuizData({
            title: "",
            passing_score: 70,
            max_attempts: 3,
            time_limit_minutes: 15,
            questions: [],
          });
          queryClient.invalidateQueries({
            queryKey: ["academy", "curriculum", createdCourseId],
          });
        },
        onError: (error) => {
          const err = handleError(error, "إنشاء الاختبار");
          toast.error(err.message);
        },
      }
    );
  }, [selectedNodeIdForQuiz, quizData, createQuiz, queryClient, createdCourseId]);

  // دالة إضافة سؤال
  const handleAddQuestion = useCallback(() => {
    if (!currentQuestion.text.trim() || !currentQuestion.correct_answer.trim()) {
      toast.error("يرجى كتابة السؤال وتحديد الإجابة الصحيحة.");
      return;
    }
    setQuizData({
      ...quizData,
      questions: [...quizData.questions, { ...currentQuestion, id: Date.now() }],
    });
    setCurrentQuestion({
      id: 1,
      type: "MCQ",
      text: "",
      options: ["", "", "", ""],
      correct_answer: "",
      points: 1,
    });
    toast.success("تم إدراج السؤال بنجاح!");
  }, [currentQuestion, quizData]);

  // معالج السحب والإفلات
  const handleDragEnd = useCallback(
    (result: any) => {
      if (!result.destination) return;

      if (result.type === "UNIT") {
        const newUnits = Array.from(localUnits);
        const [reordered] = newUnits.splice(result.source.index, 1);
        newUnits.splice(result.destination.index, 0, reordered);
        setLocalUnits(newUnits);
        // TODO: إرسال الترتيب الجديد إلى الخادم
      } else if (result.type === "NODE") {
        const unitId = Number(result.source.droppableId.split("-")[1]);
        const destUnitId = Number(result.destination.droppableId.split("-")[1]);

        if (unitId !== destUnitId) return;

        const newNodes = Array.from(localNodes);
        const unitNodes = newNodes.filter((n: any) => n.unit_id === unitId);
        const otherNodes = newNodes.filter((n: any) => n.unit_id !== unitId);

        const [movedNode] = unitNodes.splice(result.source.index, 1);
        unitNodes.splice(result.destination.index, 0, movedNode);

        setLocalNodes([...otherNodes, ...unitNodes]);
        // TODO: إرسال الترتيب الجديد إلى الخادم
      }
    },
    [localUnits, localNodes]
  );

  // ==========================================
  // 🟢 6. التصيير الرئيسي
  // ==========================================

  const isSaving = createCourse.isPending || updateCourse.isPending;

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-6xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* Header */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/60 backdrop-blur-2xl border border-primary/20 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-72 h-72 bg-primary/20 blur-[150px] rounded-full pointer-events-none -z-10" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary flex items-center gap-4 drop-shadow-sm">
            استوديو الإبداع الأكاديمي
          </h1>
          <p className="text-muted-foreground mt-3 text-lg md:text-xl font-medium">
            قم بصياغة المسارات التعليمية واربطها بهيكلك التنظيمي مباشرة.
          </p>
        </div>
        <Button
          onClick={handleSaveCourse}
          disabled={isSaving}
          size="lg"
          className="h-16 px-10 text-xl font-bold shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-all rounded-2xl w-full md:w-auto"
        >
          {isSaving ? (
            <Loader2 className="mr-2 h-6 w-6 animate-spin" />
          ) : (
            <Save className="mr-2 h-6 w-6" />
          )}
          {createdCourseId ? "حفظ التعديلات" : "اعتماد الكورس السيادي"}
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap md:flex-nowrap w-full gap-3 p-2 bg-card/40 backdrop-blur-xl border border-white/5 rounded-2xl shadow-inner">
        {[
          { id: "basic", label: "الإعدادات والتوثيق", icon: Settings },
          { id: "curriculum", label: "المنهج والدروس", icon: BookOpen },
          { id: "storage", label: "التخزين السيادي", icon: Cloud },
          { id: "adaptive", label: "مختبر AI", icon: BrainCircuit },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            disabled={!createdCourseId && tab.id !== "basic"}
            className={`flex-1 flex items-center justify-center gap-2 py-4 px-4 rounded-xl text-lg font-bold transition-all duration-300 ${
              activeTab === tab.id
                ? "bg-primary text-primary-foreground shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)]"
                : !createdCourseId && tab.id !== "basic"
                ? "opacity-40 cursor-not-allowed text-muted-foreground"
                : "text-foreground hover:bg-background/50 cursor-pointer border border-transparent hover:border-white/10"
            }`}
          >
            <tab.icon className="h-5 w-5" /> {tab.label}
          </button>
        ))}
      </div>

      <div className="w-full flex flex-col">
        {/* Basic Tab */}
        {activeTab === "basic" && (
          <Card className="w-full border-white/10 bg-card/40 backdrop-blur-2xl shadow-lg rounded-[2rem] overflow-hidden">
            <CardContent className="p-6 md:p-10">
              <CourseBasicInfo
                courseData={courseData}
                setCourseData={setCourseData}
                orgEntities={orgEntities}
                isOrgsLoading={isOrgsLoading}
                bootcamps={bootcamps}
                tracks={tracks}
                courseThumbnailFile={courseThumbnailFile}
                setCourseThumbnailFile={setCourseThumbnailFile}
                createdCourseId={createdCourseId}
              />
            </CardContent>
          </Card>
        )}

        {/* Curriculum Tab */}
        {activeTab === "curriculum" && createdCourseId && (
          <CurriculumBuilder
            createdCourseId={createdCourseId}
            localUnits={localUnits}
            setLocalUnits={setLocalUnits}
            localNodes={localNodes}
            setLocalNodes={setLocalNodes}
            isCurriculumLoading={isCurriculumLoading}
            mutations={mutations}
            handleDragEnd={handleDragEnd}
            editingUnitId={editingUnitId}
            setEditingUnitId={setEditingUnitId}
            editUnitTitle={editUnitTitle}
            setEditUnitTitle={setEditUnitTitle}
            editingNodeId={editingNodeId}
            setEditingNodeId={setEditingNodeId}
            editNodeTitle={editNodeTitle}
            setEditNodeTitle={setEditNodeTitle}
            setIsUnitModalOpen={setIsUnitModalOpen}
            setIsNodeModalOpen={setIsNodeModalOpen}
            setSelectedUnitIdForNode={setSelectedUnitIdForNode}
            setIsMaterialModalOpen={setIsMaterialModalOpen}
            setSelectedNodeIdForMaterial={setSelectedNodeIdForMaterial}
            setIsQuizModalOpen={setIsQuizModalOpen}
            setSelectedNodeIdForQuiz={setSelectedNodeIdForQuiz}
          />
        )}

        {/* Storage Tab */}
        {activeTab === "storage" && createdCourseId && (
          <Card className="w-full border-white/10 bg-card/40 backdrop-blur-2xl shadow-lg rounded-[2rem] p-8 text-center">
            <Cloud className="h-16 w-16 mx-auto text-primary/30 mb-4" />
            <h2 className="text-2xl font-bold">التخزين السيادي جاهز</h2>
            <p className="text-muted-foreground mt-2">
              يمكنك إدارة ملفات الكورس من خلال واجهة ربط المحتوى في المنهج.
            </p>
          </Card>
        )}

        {/* Adaptive Tab */}
        {activeTab === "adaptive" && createdCourseId && (
          <Card className="w-full border-white/10 bg-card/40 backdrop-blur-2xl shadow-lg rounded-[2rem] p-8 text-center">
            <BrainCircuit className="h-16 w-16 mx-auto text-primary/30 mb-4" />
            <h2 className="text-2xl font-bold">مختبر العقل الاصطناعي متصل</h2>
            <p className="text-muted-foreground mt-2">
              سيتم تفعيل التوصيات الذكية والتكيف مع مستوى الطالب قريباً.
            </p>
          </Card>
        )}
      </div>

      {/* ========================================== */}
      {/* 🟢 النوافذ المنبثقة (Modals) */}
      {/* ========================================== */}

      {/* وحدة جديدة */}
      {isUnitModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in">
          <div className="bg-card/90 backdrop-blur-3xl border border-white/10 rounded-[2rem] p-8 max-w-md w-full shadow-2xl">
            <h2 className="text-2xl font-black mb-6">تأسيس وحدة جديدة</h2>
            <Input
              placeholder="عنوان الوحدة"
              value={unitData.title}
              onChange={(e) => setUnitData({ ...unitData, title: e.target.value })}
              className="h-12 bg-background/50 border-white/10 rounded-xl"
            />
            <Input
              placeholder="وصف الوحدة (اختياري)"
              value={unitData.description}
              onChange={(e) =>
                setUnitData({ ...unitData, description: e.target.value })
              }
              className="h-12 mt-3 bg-background/50 border-white/10 rounded-xl"
            />
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="ghost" onClick={() => setIsUnitModalOpen(false)}>
                إلغاء
              </Button>
              <Button onClick={handleSaveUnit} disabled={createUnit.isPending}>
                {createUnit.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : null}
                اعتماد
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* درس جديد */}
      {isNodeModalOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-card border border-primary/20 shadow-[0_0_40px_-10px_rgba(var(--primary-rgb),0.3)] rounded-3xl p-8 max-w-md w-full my-8 animate-in fade-in zoom-in">
            <h2 className="text-2xl font-bold mb-6 text-foreground flex items-center gap-2">
              <Video className="h-6 w-6 text-primary" /> صياغة درس تفاعلي
            </h2>
            <div className="space-y-4">
              <div>
                <Label>عنوان الدرس</Label>
                <Input
                  value={nodeData.title || ""}
                  onChange={(e) =>
                    setNodeData({ ...nodeData, title: e.target.value })
                  }
                  placeholder="مثال: مقدمة في الخوارزميات"
                  className="bg-background/50 h-12 rounded-xl mt-2 border-white/10"
                />
              </div>
              <div>
                <Label>نوع الدرس</Label>
                <select
                  className="w-full h-12 px-4 mt-2 bg-background/50 border border-white/10 rounded-xl outline-none focus:border-primary shadow-inner"
                  value={nodeData.content_type}
                  onChange={(e) =>
                    setNodeData({ ...nodeData, content_type: e.target.value })
                  }
                >
                  <option value="MATERIAL">محتوى علمي (فيديو / مقال / ملف)</option>
                  <option value="QUIZ">اختبار تقييمي (Quiz)</option>
                  <option value="LIVE">بث مباشر (Zoom / Meet)</option>
                  <option value="TASK">تلميح تكليف (Task Link)</option>
                </select>
              </div>

              {nodeData.content_type === "LIVE" && (
                <div className="space-y-4 mt-4 p-4 bg-blue-500/10 rounded-xl border border-blue-500/20">
                  <Label className="text-blue-500 font-bold flex items-center gap-2">
                    <Video className="w-4 h-4" /> إعدادات البث المباشر
                  </Label>
                  <Input
                    type="datetime-local"
                    value={nodeData.scheduled_start || ""}
                    onChange={(e) =>
                      setNodeData({ ...nodeData, scheduled_start: e.target.value })
                    }
                    className="bg-background/50 mt-2 border-white/10"
                  />
                  <Input
                    type="url"
                    placeholder="رابط Zoom أو Google Meet..."
                    value={nodeData.meeting_url || ""}
                    onChange={(e) =>
                      setNodeData({ ...nodeData, meeting_url: e.target.value })
                    }
                    className="bg-background/50 mt-2 border-white/10"
                  />
                </div>
              )}

              {nodeData.content_type === "TASK" && (
                <div className="space-y-2 mt-4 p-4 bg-orange-500/10 rounded-xl border border-orange-500/20">
                  <Label className="text-orange-500 font-bold flex items-center gap-2">
                    <Target className="w-4 h-4" /> ربط تكليف موازي
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    سيظهر للطالب هنا بطاقة تنبيهية توجهه إلى صفحة التكليفات لإنهاء المهمة.
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 mt-4 p-4 bg-primary/5 rounded-xl border border-primary/20">
                <div className="col-span-2">
                  <Label className="flex items-center gap-2 text-primary font-bold">
                    <BrainCircuit className="h-4 w-4" /> الجيميفيكيشن (مكافأة الإنجاز)
                  </Label>
                </div>
                <div>
                  <Label>نقاط الخبرة (Reward)</Label>
                  <Input
                    type="number"
                    value={nodeData.reward_amount || ""}
                    onChange={(e) =>
                      setNodeData({ ...nodeData, reward_amount: e.target.value })
                    }
                    placeholder="50"
                    className="bg-background/50 mt-2 border-white/10"
                  />
                </div>
                <div>
                  <Label>نوع العملة / النقاط</Label>
                  <select
                    className="w-full h-10 px-3 mt-2 bg-background/50 border border-white/10 rounded-md outline-none"
                    value={nodeData.reward_currency || "XP"}
                    onChange={(e) =>
                      setNodeData({ ...nodeData, reward_currency: e.target.value })
                    }
                  >
                    <option value="XP">نقاط خبرة (XP)</option>
                    <option value="MR_USDT">رصيد (MR_USDT)</option>
                    <option value="NBT">عملة نبت (NBT)</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <Button variant="ghost" onClick={() => setIsNodeModalOpen(false)}>
                  إلغاء
                </Button>
                <Button onClick={handleSaveNode} disabled={createNode.isPending}>
                  {createNode.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  إنشاء الدرس
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ربط المحتوى */}
      {isMaterialModalOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-background/90 backdrop-blur-md p-4">
          <div className="bg-card border border-primary/20 shadow-[0_0_40px_-10px_rgba(var(--primary-rgb),0.3)] rounded-3xl p-8 max-w-md w-full animate-in fade-in zoom-in">
            <h2 className="text-2xl font-bold mb-6">ربط المحتوى الأكاديمي</h2>
            <div className="space-y-4">
              <div>
                <Label>عنوان المحتوى</Label>
                <Input
                  value={materialData.title || ""}
                  onChange={(e) =>
                    setMaterialData({ ...materialData, title: e.target.value })
                  }
                  placeholder="مثال: فيديو الشرح الأساسي"
                  className="mt-2 bg-background/50 border-white/10"
                />
              </div>
              <div>
                <Label>نوع المحتوى</Label>
                <select
                  className="w-full h-12 px-4 mt-2 bg-background/50 border border-white/10 rounded-xl outline-none"
                  value={materialData.material_type}
                  onChange={(e) =>
                    setMaterialData({ ...materialData, material_type: e.target.value })
                  }
                >
                  <option value="YOUTUBE">مقطع يوتيوب (YouTube)</option>
                  <option value="LINK">رابط خارجي (External Link)</option>
                  <option value="PDF">ملف سيادي (PDF)</option>
                  <option value="DOC">مستند (DOC)</option>
                </select>
              </div>

              {["YOUTUBE", "LINK"].includes(materialData.material_type) ? (
                <div>
                  <Label>الرابط (URL)</Label>
                  <Input
                    value={materialData.file_url || ""}
                    onChange={(e) =>
                      setMaterialData({ ...materialData, file_url: e.target.value })
                    }
                    placeholder="https://youtube.com/..."
                    className="mt-2 bg-background/50 border-white/10"
                  />
                </div>
              ) : (
                <div>
                  <Label>رفع الملف (MinIO)</Label>
                  <Input
                    type="file"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="mt-2 pt-2 bg-background/50 border-white/10"
                  />
                </div>
              )}

              <div className="flex items-center gap-2 mt-4">
                <input
                  type="checkbox"
                  id="downloadable"
                  checked={materialData.is_downloadable}
                  onChange={(e) =>
                    setMaterialData({
                      ...materialData,
                      is_downloadable: e.target.checked,
                    })
                  }
                  className="h-4 w-4 rounded border-primary text-primary"
                />
                <Label htmlFor="downloadable">السماح للطالب بتحميل الملف</Label>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <Button variant="ghost" onClick={() => setIsMaterialModalOpen(false)}>
                  إلغاء
                </Button>
                <Button
                  onClick={handleSaveMaterial}
                  disabled={createMaterial.isPending}
                >
                  {createMaterial.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  ربط المحتوى
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* مصنع الاختبارات */}
      {isQuizModalOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-background/90 backdrop-blur-md p-4 overflow-y-auto">
          <div className="bg-card border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.3)] rounded-[2rem] p-8 max-w-3xl w-full my-8 animate-in fade-in zoom-in">
            <h2 className="text-3xl font-bold mb-6 text-primary flex items-center gap-3">
              <BrainCircuit className="h-8 w-8" /> مصنع الاختبارات التكيفية
            </h2>

            <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-background/50 rounded-2xl border border-white/5">
              <div>
                <Label>عنوان الاختبار</Label>
                <Input
                  value={quizData.title || ""}
                  onChange={(e) =>
                    setQuizData({ ...quizData, title: e.target.value })
                  }
                  className="mt-2 bg-background/50 border-white/10"
                />
              </div>
              <div>
                <Label>درجة النجاح (%)</Label>
                <Input
                  type="number"
                  value={quizData.passing_score}
                  onChange={(e) =>
                    setQuizData({ ...quizData, passing_score: Number(e.target.value) })
                  }
                  className="mt-2 bg-background/50 border-white/10"
                />
              </div>
            </div>

            <div className="p-6 bg-primary/5 rounded-2xl border border-primary/20 mb-6">
              <h3 className="text-xl font-bold mb-4">صياغة سؤال جديد</h3>
              <div className="space-y-4">
                <div>
                  <Label>نص السؤال</Label>
                  <Input
                    placeholder="اكتب سؤالك هنا..."
                    value={currentQuestion.text || ""}
                    onChange={(e) =>
                      setCurrentQuestion({ ...currentQuestion, text: e.target.value })
                    }
                    className="mt-2 bg-background/50 border-white/10"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {currentQuestion.options.map((opt, idx) => (
                    <div key={idx}>
                      <Label>الخيار {idx + 1}</Label>
                      <Input
                        value={opt || ""}
                        onChange={(e) => {
                          const newOpts = [...currentQuestion.options];
                          newOpts[idx] = e.target.value;
                          setCurrentQuestion({
                            ...currentQuestion,
                            options: newOpts,
                          });
                        }}
                        className="mt-1 bg-background/50 border-white/10"
                      />
                    </div>
                  ))}
                </div>

                <div>
                  <Label className="text-emerald-500 font-bold">
                    الإجابة الصحيحة (تطابق أحد الخيارات)
                  </Label>
                  <Input
                    value={currentQuestion.correct_answer || ""}
                    onChange={(e) =>
                      setCurrentQuestion({
                        ...currentQuestion,
                        correct_answer: e.target.value,
                      })
                    }
                    className="mt-2 border-emerald-500/50 bg-background/50"
                  />
                </div>

                <Button
                  onClick={handleAddQuestion}
                  variant="secondary"
                  className="w-full mt-2 font-bold shadow-md"
                >
                  <Plus className="ml-2 h-5 w-5" /> إدراج السؤال في الاختبار
                </Button>
              </div>
            </div>

            {quizData.questions.length > 0 && (
              <div className="mb-6 space-y-2">
                <Label className="font-bold text-lg">
                  الأسئلة المعتمدة ({quizData.questions.length}):
                </Label>
                {quizData.questions.map((q, i) => (
                  <div
                    key={i}
                    className="p-4 bg-background/50 border border-white/5 rounded-xl flex justify-between items-center shadow-sm"
                  >
                    <span className="font-medium text-lg">
                      {i + 1}. {q.text}
                    </span>
                    <span className="text-sm bg-emerald-500/10 text-emerald-500 px-3 py-1.5 rounded-lg font-bold border border-emerald-500/20">
                      الإجابة: {q.correct_answer}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end gap-3 mt-8">
              <Button
                variant="ghost"
                onClick={() => setIsQuizModalOpen(false)}
                className="rounded-xl h-12 px-6"
              >
                إلغاء وإغلاق
              </Button>
              <Button
                onClick={handleSaveQuiz}
                disabled={createQuiz.isPending}
                size="lg"
                className="rounded-xl shadow-xl px-8 h-12 text-lg"
              >
                {createQuiz.isPending ? (
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                ) : null}
                اعتماد الاختبار السيادي
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}