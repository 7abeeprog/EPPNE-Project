// app/public-entity/[id]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { ComponentRenderer } from "@/components/brand-builder/component-renderer";
import { Loader2, ShieldCheck } from "lucide-react";

export default function PublicEntityPage() {
  const params = useParams();
  const entityId = params.id;
  const [pageData, setPageData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPage = async () => {
      try {
        // جلب تصميم الصفحة من الباك إند
        const res = await apiClient.get(`/sovereign-entities/${entityId}/page`);
        setPageData(res.data);
      } catch (error) {
        console.error("Failed to load page", error);
      } finally {
        setLoading(false);
      }
    };
    fetchPage();
  }, [entityId]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background">
        <Loader2 className="animate-spin h-12 w-12 text-primary mb-4" />
        <p className="text-primary font-mono tracking-widest animate-pulse">جاري تحميل الكيان السيادي...</p>
      </div>
    );
  }

  if (!pageData || !pageData.page?.structure) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <ShieldCheck className="h-16 w-16 text-muted-foreground mx-auto opacity-20" />
          <h1 className="text-2xl font-bold text-muted-foreground">الصفحة غير موجودة أو قيد التأسيس</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
      {/* رسم أقسام الصفحة بناءً على التصميم الذي تم سحبه وإفلاته */}
      {pageData.page.structure.sections.map((section: any) => (
        <section key={section.id} className={`w-full ${section.layout === "grid" ? "max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 px-4 py-12" : "py-4"}`}>
          {section.components.map((comp: any) => (
            // 🟢 استخدام isPreviewMode لإخفاء حدود التعديل وأدوات الحذف
            <ComponentRenderer key={comp.id} component={comp} isPreviewMode={true} />
          ))}
        </section>
      ))}
    </div>
  );
}