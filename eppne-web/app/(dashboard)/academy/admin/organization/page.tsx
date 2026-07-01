// app/(dashboard)/academy/admin/organization/page.tsx
"use client";

import { useState, useMemo, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";

// ✅ استبدال enterprise-store بالهوكات الجديدة
import { useOrganizationEntities, useCreateOrganizationEntity } from "@/hooks/academy-queries";
import { OrganizationEntity } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Network,
  Plus,
  Building2,
  GraduationCap,
  Layers,
  School,
  Building,
  Briefcase,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

// ✅ دالة مساعدة للأيقونات (محسّنة)
const getEntityIcon = (type: string) => {
  const iconClass = "h-6 w-6 drop-shadow-sm";
  switch (type) {
    case "MINISTRY":
      return <Building className={`${iconClass} text-blue-500`} />;
    case "DIRECTORATE":
      return <Building2 className={`${iconClass} text-cyan-500`} />;
    case "UNIVERSITY":
      return <GraduationCap className={`${iconClass} text-purple-500`} />;
    case "COLLEGE":
      return <Building2 className={`${iconClass} text-indigo-500`} />;
    case "SCHOOL":
      return <School className={`${iconClass} text-emerald-500`} />;
    case "NURSERY":
      return <School className={`${iconClass} text-pink-500`} />;
    case "DEPARTMENT":
      return <Layers className={`${iconClass} text-orange-500`} />;
    case "COMPANY":
      return <Briefcase className={`${iconClass} text-cyan-500`} />;
    default:
      return <Network className={`${iconClass} text-primary`} />;
  }
};

// ✅ دالة مساعدة لترجمة نوع الكيان
const getEntityTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    MINISTRY: "وزارة",
    DIRECTORATE: "مديرية",
    UNIVERSITY: "جامعة",
    COLLEGE: "كلية",
    SCHOOL: "مدرسة",
    NURSERY: "حضانة",
    DEPARTMENT: "قسم",
    COMPANY: "شركة",
  };
  return labels[type] || type;
};

// ✅ مكون عقدة الشجرة (محسّن مع React.memo)
const OrgTreeNode = React.memo(
  ({
    entity,
    allEntities,
    onAddChild,
  }: {
    entity: OrganizationEntity;
    allEntities: OrganizationEntity[];
    onAddChild: (parentId: number) => void;
  }) => {
    const children = allEntities.filter((e) => e.parent_id === entity.id);

    return (
      <div className="mt-4 animate-in fade-in zoom-in-95 duration-300">
        <div className="flex items-center justify-between p-5 bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl hover:border-primary/50 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group relative overflow-hidden">
          <div className="absolute top-0 right-0 w-1 h-full bg-gradient-to-b from-primary/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="flex items-center gap-4 relative z-10">
            <div className="p-3 bg-background/50 rounded-xl border border-border/50 shadow-inner group-hover:scale-110 transition-transform">
              {getEntityIcon(entity.entity_type)}
            </div>
            <div>
              <h3 className="text-xl font-black flex items-center gap-3 text-foreground group-hover:text-primary transition-colors">
                {entity.name}
                <span className="text-xs font-bold px-3 py-1 bg-primary/10 text-primary border border-primary/20 rounded-md shadow-sm">
                  {getEntityTypeLabel(entity.entity_type)}
                </span>
              </h3>
              {entity.description && (
                <p className="text-sm text-muted-foreground mt-1.5 font-medium">
                  {entity.description}
                </p>
              )}
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="opacity-0 group-hover:opacity-100 transition-all border-primary/30 text-primary hover:bg-primary/10 hover:text-primary rounded-xl h-10 px-4 shadow-md relative z-10"
            onClick={() => onAddChild(entity.id)}
          >
            <Plus className="h-4 w-4 ml-2" /> تفريع سيادي
          </Button>
        </div>

        {children.length > 0 && (
          <div className="pr-10 mt-3 border-r-2 border-dashed border-primary/20 mr-8 space-y-2 relative">
            <div className="absolute top-0 right-[-2px] w-4 h-4 bg-primary/20 rounded-full blur-[2px]" />
            {children.map((child) => (
              <OrgTreeNode
                key={child.id}
                entity={child}
                allEntities={allEntities}
                onAddChild={onAddChild}
              />
            ))}
          </div>
        )}
      </div>
    );
  }
);

OrgTreeNode.displayName = "OrgTreeNode";

export default function OrganizationPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [parentId, setParentId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    entity_type: "UNIVERSITY",
    description: "",
  });

  // ✅ 1. جلب الكيانات التنظيمية (مع Pagination)
  const {
    data: orgEntitiesData,
    isLoading: isEntitiesLoading,
    error: entitiesError,
  } = useOrganizationEntities(0, 500); // حد معقول للشجرة

  const orgEntities = orgEntitiesData?.data || [];

  // ✅ 2. حساب الكيانات الجذرية (useMemo)
  const rootEntities = useMemo(() => {
    return orgEntities.filter((e: OrganizationEntity) => !e.parent_id);
  }, [orgEntities]);

  // ✅ 3. محرك التأسيس (Mutation)
  const createEntityMutation = useCreateOrganizationEntity();

  // ✅ 4. معالجة الأخطاء
  if (entitiesError) {
    const error = handleError(entitiesError, "جلب الهيكل التنظيمي");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل الهيكل التنظيمي</h2>
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

  // ✅ 5. دوال التفاعل
  const handleOpenModal = useCallback((parent: number | null = null) => {
    setParentId(parent);
    setFormData({
      name: "",
      entity_type: parent ? "COLLEGE" : "UNIVERSITY",
      description: "",
    });
    setIsModalOpen(true);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error("اسم الكيان مطلوب.");
      return;
    }

    createEntityMutation.mutate(
      {
        name: formData.name.trim(),
        entity_type: formData.entity_type,
        description: formData.description.trim() || undefined,
        parent_id: parentId,
        // tenant_id يتم تعبئته تلقائياً في AcademyService
      },
      {
        onSuccess: () => {
          toast.success("تم تشفير واعتماد الكيان التنظيمي بنجاح!");
          queryClient.invalidateQueries({
            queryKey: ["academy", "organization-entities"],
          });
          setIsModalOpen(false);
          setFormData({ name: "", entity_type: "UNIVERSITY", description: "" });
        },
        onError: (error) => {
          const err = handleError(error, "تأسيس الكيان التنظيمي");
          toast.error(err.message);
        },
      }
    );
  };

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(var(--primary-rgb),0.05),_transparent_70%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-72 h-72 bg-primary/20 blur-[150px] rounded-full pointer-events-none -z-10" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary flex items-center gap-4 drop-shadow-sm">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner">
              <Network className="h-10 w-10 text-primary" />
            </div>
            الهيكل التنظيمي السيادي
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            قم بصياغة شجرة المؤسسات، الكليات، والأقسام بدقة عسكرية لضمان تراتبية الصلاحيات والمسارات.
          </p>
        </div>
        <Button
          onClick={() => handleOpenModal(null)}
          size="lg"
          className="h-16 px-8 text-xl font-bold shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-transform rounded-2xl w-full md:w-auto"
        >
          <Plus className="ml-2 h-6 w-6" /> تأسيس كيان جذري
        </Button>
      </div>

      {/* مساحة العرض (شجرة الكيانات) */}
      <div className="bg-card/20 backdrop-blur-md p-8 rounded-[2.5rem] border border-white/5 shadow-inner min-h-[500px] relative overflow-hidden">
        <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-background/50 to-transparent pointer-events-none" />

        {isEntitiesLoading ? (
          <div className="space-y-6">
            {[1, 2].map((i) => (
              <div key={i} className="space-y-4">
                <Skeleton className="h-24 w-full rounded-2xl bg-card/50 border border-white/5" />
                <div className="pr-12 space-y-4">
                  <Skeleton className="h-20 w-3/4 rounded-2xl bg-card/30 border border-white/5" />
                </div>
              </div>
            ))}
          </div>
        ) : orgEntities.length === 0 ? (
          <div className="text-center py-32 relative z-10 border border-dashed border-primary/20 rounded-[2rem] bg-background/30">
            <Network className="h-20 w-20 mx-auto text-primary/30 mb-6 animate-pulse" />
            <h3 className="text-3xl font-black text-foreground">الخريطة التنظيمية فارغة</h3>
            <p className="text-muted-foreground mt-3 text-lg">
              ابدأ بتأسيس أول كيان جذري (جامعة، وزارة، أو هيئة) لتبدأ التفرع.
            </p>
          </div>
        ) : (
          <div className="relative z-10 pb-20">
            {rootEntities.map((root: OrganizationEntity) => (
              <OrgTreeNode
                key={root.id}
                entity={root}
                allEntities={orgEntities}
                onAddChild={handleOpenModal}
              />
            ))}
          </div>
        )}
      </div>

      {/* نافذة التأسيس الزجاجية (Modal) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="bg-card/90 backdrop-blur-3xl border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.3)] rounded-[2.5rem] p-8 md:p-10 max-w-lg w-full animate-in zoom-in-95 duration-300">
            <h2 className="text-3xl font-black mb-8 flex items-center gap-3 border-b border-border/50 pb-6 text-foreground">
              <div className="p-2 bg-primary/10 rounded-xl border border-primary/20">
                <Network className="h-8 w-8 text-primary" />
              </div>
              {parentId ? "إضافة تفريع جديد" : "تأسيس كيان جذري"}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-3">
                <Label className="font-bold text-lg">الاسم الكودي للكيان</Label>
                <Input
                  placeholder="مثال: كلية الذكاء الاصطناعي"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-primary text-lg transition-colors shadow-inner"
                  required
                />
              </div>
              <div className="space-y-3">
                <Label className="font-bold text-lg">التصنيف السيادي (النوع)</Label>
                <select
                  className="w-full h-14 px-4 rounded-xl border border-white/10 bg-background/50 text-lg focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all cursor-pointer shadow-inner"
                  value={formData.entity_type}
                  onChange={(e) =>
                    setFormData({ ...formData, entity_type: e.target.value })
                  }
                >
                  <option value="MINISTRY" className="font-bold">
                    وزارة / هيئة عليا
                  </option>
                  <option value="DIRECTORATE">مديرية / منطقة</option>
                  <option value="UNIVERSITY" className="font-bold text-primary">
                    جامعة / أكاديمية
                  </option>
                  <option value="COLLEGE">كلية / قطاع</option>
                  <option value="DEPARTMENT">قسم أكاديمي</option>
                  <option value="SCHOOL">مدرسة</option>
                  <option value="NURSERY">حضانة</option>
                  <option value="COMPANY">شركة / مركز تدريب</option>
                </select>
              </div>
              <div className="space-y-3">
                <Label className="font-bold text-lg">الوصف العسكري (اختياري)</Label>
                <Input
                  placeholder="نبذة عن مهام هذا الكيان..."
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-primary text-lg transition-colors shadow-inner"
                />
              </div>
              <div className="flex justify-end gap-4 mt-10 pt-6 border-t border-border/50">
                <Button
                  type="button"
                  variant="ghost"
                  className="rounded-xl h-14 px-8 text-lg font-bold"
                  onClick={() => setIsModalOpen(false)}
                >
                  إلغاء التشفير
                </Button>
                <Button
                  type="submit"
                  disabled={createEntityMutation.isPending}
                  className="rounded-xl h-14 px-10 text-lg font-bold shadow-[0_0_20px_rgba(var(--primary-rgb),0.4)] hover:scale-105 transition-transform"
                >
                  {createEntityMutation.isPending ? (
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  ) : null}
                  {createEntityMutation.isPending
                    ? "جاري التأسيس..."
                    : "اعتماد الكيان"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}