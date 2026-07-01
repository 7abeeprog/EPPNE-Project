// app/(dashboard)/academy/admin/entities/page.tsx
"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { motion, Variants } from "framer-motion";
import Link from "next/link";

// ✅ الهوكات والأنواع السيادية
import { useOrganizationEntities } from "@/hooks/academy-queries";
import { OrganizationEntity } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Network,
  Search,
  Building2,
  GraduationCap,
  Layers,
  School,
  Building,
  Briefcase,
  Plus,
  AlertCircle,
  Filter,
  ChevronRight,
} from "lucide-react";

// ✅ واجهات محلية لضمان أمان نوع البيانات القادمة من الـ API
interface PaginatedResponse<T> {
  data: T[];
  total?: number;
}

interface InfiniteEntitiesData {
  pages?: PaginatedResponse<OrganizationEntity>[];
  data?: OrganizationEntity[];
}

// ✅ دالة أيقونة الكيان
const getEntityIcon = (type: string) => {
  const iconClass = "h-6 w-6 drop-shadow-sm";
  switch (type) {
    case "MINISTRY": return <Building className={`${iconClass} text-blue-500`} />;
    case "DIRECTORATE": return <Building2 className={`${iconClass} text-cyan-500`} />;
    case "UNIVERSITY": return <GraduationCap className={`${iconClass} text-purple-500`} />;
    case "COLLEGE": return <Building2 className={`${iconClass} text-indigo-500`} />;
    case "SCHOOL": return <School className={`${iconClass} text-emerald-500`} />;
    case "DEPARTMENT": return <Layers className={`${iconClass} text-orange-500`} />;
    case "COMPANY": return <Briefcase className={`${iconClass} text-cyan-500`} />;
    default: return <Network className={`${iconClass} text-primary`} />;
  }
};

const getEntityTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    MINISTRY: "وزارة",
    DIRECTORATE: "مديرية",
    UNIVERSITY: "جامعة",
    COLLEGE: "كلية",
    SCHOOL: "مدرسة",
    DEPARTMENT: "قسم",
    COMPANY: "شركة",
  };
  return labels[type] || type;
};

const getEntityTypeColor = (type: string) => {
  switch (type) {
    case "MINISTRY": return "bg-blue-500/10 text-blue-500 border-blue-500/20";
    case "DIRECTORATE": return "bg-cyan-500/10 text-cyan-500 border-cyan-500/20";
    case "UNIVERSITY": return "bg-purple-500/10 text-purple-500 border-purple-500/20";
    case "COLLEGE": return "bg-indigo-500/10 text-indigo-500 border-indigo-500/20";
    case "SCHOOL": return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
    case "DEPARTMENT": return "bg-orange-500/10 text-orange-500 border-orange-500/20";
    case "COMPANY": return "bg-cyan-500/10 text-cyan-500 border-cyan-500/20";
    default: return "bg-primary/10 text-primary border-primary/20";
  }
};

// ✅ تعريف الحركات الصارمة لمنع أخطاء الـ Index Signature
const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

export default function EntitiesDashboard() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [filterType, setFilterType] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(0);
  const limit = 20;

  // ✅ 1. جلب الكيانات التنظيمية
  const { data: entitiesData, isLoading, error } = useOrganizationEntities();

  // ✅ 2. استخراج البيانات مع حماية لا تخترق ضد الـ Unknown/Implicit Any
  const entities = useMemo(() => {
    if (!entitiesData) return [];
    
    // تأكيد النوع بشكل صارم للتعامل الآمن مع بيانات الـ Query
    const safeData = entitiesData as unknown as InfiniteEntitiesData;
    
    if (safeData.pages && Array.isArray(safeData.pages)) {
      return safeData.pages.flatMap((page) => page.data || []);
    }
    
    if (safeData.data && Array.isArray(safeData.data)) {
      return safeData.data;
    }

    return [];
  }, [entitiesData]);

  // ✅ 3. تصفية الكيانات بكفاءة عالية (O(N))
  const filteredEntities = useMemo(() => {
    let result = entities;
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (entity) =>
          entity.name.toLowerCase().includes(query) ||
          entity.entity_type.toLowerCase().includes(query)
      );
    }
    if (filterType) {
      result = result.filter((entity) => entity.entity_type === filterType);
    }
    return result;
  }, [entities, searchQuery, filterType]);

  // ✅ 4. Pagination محلية
  const totalPages = Math.max(1, Math.ceil(filteredEntities.length / limit));
  const paginatedEntities = useMemo(() => {
    return filteredEntities.slice(currentPage * limit, (currentPage + 1) * limit);
  }, [filteredEntities, currentPage, limit]);

  const handleNextPage = () => {
    if (currentPage < totalPages - 1) setCurrentPage((p) => p + 1);
  };

  const handlePrevPage = () => {
    if (currentPage > 0) setCurrentPage((p) => p - 1);
  };

  // ✅ 5. معالجة الأخطاء السيادية
  if (error) {
    const err = handleError(error, "جلب الكيانات التنظيمية");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center animate-in zoom-in-95 duration-500">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20 shadow-[0_0_30px_rgba(var(--destructive-rgb),0.2)]">
          <AlertCircle className="h-16 w-16 text-destructive animate-pulse" />
        </div>
        <h2 className="text-3xl font-black mb-2 text-foreground">فشل في استرداد الهيكل التنظيمي</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{err.message}</p>
        <Button onClick={() => window.location.reload()} size="lg" className="rounded-xl h-14 px-8 font-bold shadow-lg hover:scale-105 transition-transform">
          إعادة إنشاء الاتصال
        </Button>
      </div>
    );
  }

  // ✅ 6. استخراج أنواع الكيانات الديناميكية للفلترة
  const entityTypes = useMemo(() => {
    const types = new Set<string>();
    entities.forEach((entity) => types.add(entity.entity_type));
    return Array.from(types);
  }, [entities]);

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(99,102,241,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2.5rem] bg-card/40 backdrop-blur-2xl border border-white/5 shadow-[0_0_50px_-15px_rgba(99,102,241,0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-72 h-72 bg-indigo-500/10 blur-[100px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-indigo-500 flex items-center gap-4 drop-shadow-md">
            <div className="p-4 bg-indigo-500/10 rounded-2xl border border-indigo-500/20 shadow-inner">
              <Network className="h-10 w-10 text-indigo-500" />
            </div>
            الكيانات التنظيمية
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            نظام التحكم المركزي لإدارة الهياكل المؤسسية (وزارات، جامعات، مديريات) بكفاءة سيادية.
          </p>
        </div>
        <Link href="/academy/admin/organization">
          <Button size="lg" className="h-16 px-8 text-xl font-black shadow-[0_0_25px_rgba(99,102,241,0.4)] hover:scale-105 transition-all rounded-2xl w-full md:w-auto bg-indigo-600 hover:bg-indigo-500 text-white">
            <Plus className="mr-3 h-6 w-6" />
            إدارة الشجرة التنظيمية
          </Button>
        </Link>
      </div>

      {/* شريط البحث والفلترة */}
      <Card className="w-full border-white/5 bg-card/40 backdrop-blur-xl shadow-xl rounded-[2.5rem] overflow-hidden">
        <CardContent className="p-8 space-y-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute right-4 top-1/2 -translate-y-1/2 text-indigo-500/50 h-5 w-5" />
              <Input
                placeholder="ابحث بالاسم أو رمز الكيان..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(0);
                }}
                className="w-full h-14 pr-12 text-lg rounded-xl bg-background/50 border-white/10 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all shadow-inner font-medium"
              />
            </div>
            <div className="relative w-full md:w-72">
              <Filter className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground/50 h-5 w-5" />
              <select
                className="w-full h-14 px-4 pr-12 bg-background/50 border border-white/10 rounded-xl outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all cursor-pointer shadow-inner text-lg font-bold appearance-none"
                value={filterType}
                onChange={(e) => {
                  setFilterType(e.target.value);
                  setCurrentPage(0);
                }}
              >
                <option value="">كافة التصنيفات التنظيمية</option>
                {entityTypes.map((type) => (
                  <option key={type} value={type}>
                    {getEntityTypeLabel(type)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-between items-center text-sm text-muted-foreground font-bold">
            <span>
              عرض {paginatedEntities.length} من أصل {filteredEntities.length} كيان مسجل
            </span>
            {filterType && (
              <Badge className="bg-indigo-500/10 text-indigo-500 border-indigo-500/20 px-3 py-1 cursor-pointer transition-all hover:bg-indigo-500/20" onClick={() => { setFilterType(""); setCurrentPage(0); }}>
                {getEntityTypeLabel(filterType)} ✕
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* قائمة الكيانات (Grid) */}
      <div className="w-full">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-28 rounded-[2rem] bg-card/40 border border-white/5 shadow-sm" />
            ))}
          </div>
        ) : paginatedEntities.length === 0 ? (
          <div className="text-center py-20 bg-card/20 backdrop-blur-xl rounded-[3rem] border border-dashed border-indigo-500/20 shadow-inner">
            <Network className="mx-auto h-20 w-20 text-indigo-500/20 mb-6 animate-pulse" />
            <h2 className="text-2xl font-black text-foreground drop-shadow-sm">
              {searchQuery || filterType ? "لا توجد تطابقات لعملية البحث" : "سجل الكيانات فارغ"}
            </h2>
            <p className="text-muted-foreground mt-3 text-lg font-medium">
              {searchQuery || filterType ? "الرجاء مراجعة محددات الفلترة وإعادة المحاولة." : "يجب تأسيس الشجرة التنظيمية أولاً للبدء بإدارة الكيانات."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {paginatedEntities.map((entity, index) => (
              <motion.div
                key={entity.id}
                variants={cardVariants}
                initial="hidden"
                animate="show"
                transition={{ delay: index * 0.03 }}
              >
                <Card className="border-white/5 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-indigo-500/40 hover:bg-card/60 hover:shadow-[0_10px_40px_rgba(99,102,241,0.1)] transition-all duration-300 group overflow-hidden">
                  <CardContent className="p-6 md:p-8">
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                      <div className="flex items-center gap-5 flex-1 w-full">
                        <div className="p-4 bg-background/50 rounded-2xl border border-white/5 shadow-inner group-hover:scale-105 transition-transform duration-300 group-hover:border-indigo-500/30 group-hover:bg-indigo-500/5">
                          {getEntityIcon(entity.entity_type)}
                        </div>
                        <div className="flex-1 space-y-2">
                          <div className="flex flex-wrap items-center gap-3">
                            <h3 className="text-2xl font-black text-foreground group-hover:text-indigo-500 transition-colors">
                              {entity.name}
                            </h3>
                            <Badge className={`${getEntityTypeColor(entity.entity_type)} px-3 py-1 font-bold`}>
                              {getEntityTypeLabel(entity.entity_type)}
                            </Badge>
                            {!entity.is_active && (
                              <Badge className="bg-destructive/10 text-destructive border-destructive/20 px-3 py-1 font-bold">
                                حالة معلقة
                              </Badge>
                            )}
                          </div>
                          
                          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6 text-sm text-muted-foreground font-medium">
                            {entity.parent_id && (
                              <div className="flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500/50" />
                                تابعة لـ: <span className="font-bold text-foreground">
                                  {entities.find((e) => e.id === entity.parent_id)?.name || `#${entity.parent_id}`}
                                </span>
                              </div>
                            )}
                            {entity.description && (
                              <p className="line-clamp-1 flex-1 border-r border-white/10 pr-4">
                                {entity.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 shrink-0 self-end md:self-auto">
                        <div className="bg-background/40 px-4 py-2 rounded-xl border border-white/5 shadow-inner">
                          <span className="font-mono text-sm font-bold text-muted-foreground">ID:{entity.id}</span>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="rounded-xl h-12 w-12 bg-background/30 hover:bg-indigo-500 hover:text-white transition-all shadow-sm group/btn border border-white/5 hover:border-transparent"
                          onClick={() => router.push(`/academy/admin/organization?highlight=${entity.id}`)}
                        >
                          <ChevronRight className="h-6 w-6 text-muted-foreground group-hover/btn:text-white transition-colors" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-4 pt-6 pb-2">
          <Button
            variant="outline"
            onClick={handlePrevPage}
            disabled={currentPage === 0}
            className="rounded-xl px-8 h-14 font-black text-lg border-white/10 hover:bg-white/5 hover:border-indigo-500/50 transition-all shadow-sm disabled:opacity-50"
          >
            السابق
          </Button>
          <div className="bg-card/40 backdrop-blur-md px-6 py-3 rounded-xl border border-white/5 shadow-inner font-black text-lg text-foreground">
            {currentPage + 1} <span className="text-muted-foreground font-medium mx-1">من</span> {totalPages}
          </div>
          <Button
            variant="outline"
            onClick={handleNextPage}
            disabled={currentPage >= totalPages - 1}
            className="rounded-xl px-8 h-14 font-black text-lg border-white/10 hover:bg-white/5 hover:border-indigo-500/50 transition-all shadow-sm disabled:opacity-50"
          >
            التالي
          </Button>
        </div>
      )}
    </div>
  );
}