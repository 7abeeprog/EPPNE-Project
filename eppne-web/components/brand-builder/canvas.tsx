// components/brand-builder/canvas.tsx
"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useBrandBuilderStore, Section } from "@/store/brand-builder-store";
import { SortableSection } from "./sortable-section";
import { Button } from "@/components/ui/button";
import { Plus, LayoutTemplate, Sparkles } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export function Canvas() {
  const { pageStructure, addSection } = useBrandBuilderStore();

  // 🟢 تحويل كامل مساحة العمل إلى منطقة قابلة لاستقبال العناصر
  const { setNodeRef, isOver } = useDroppable({
    id: "main-canvas-dropzone",
    data: {
      type: "canvas",
    }
  });

  // 🟢 1. حالة التحميل السيادية (Glassmorphic Skeleton)
  if (!pageStructure) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[500px] border border-white/10 rounded-[2.5rem] bg-card/30 backdrop-blur-2xl shadow-inner space-y-6 p-8 animate-in fade-in duration-700">
        <div className="p-4 bg-primary/10 rounded-2xl border border-primary/20 shadow-[0_0_30px_rgba(var(--primary-rgb),0.2)]">
          <LayoutTemplate className="h-12 w-12 text-primary animate-pulse" />
        </div>
        <div className="space-y-4 w-full max-w-md text-center">
            <p className="text-xl font-black text-foreground mb-4">جاري تهيئة مساحة العمل السيادية...</p>
            <Skeleton className="h-24 w-full bg-card/50 rounded-2xl border border-white/5" />
            <Skeleton className="h-24 w-full bg-card/50 rounded-2xl border border-white/5" />
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={setNodeRef} 
      className={`space-y-6 pb-24 min-h-[600px] transition-all duration-500 rounded-[2.5rem] p-2 md:p-4 relative ${
        isOver ? "bg-primary/5 ring-2 ring-primary/40 shadow-[0_0_50px_rgba(var(--primary-rgb),0.15)]" : "bg-transparent"
      }`}
    >
      {/* 🟢 2. حالة المساحة الفارغة (Empty State) */}
      {pageStructure.sections.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed border-primary/30 rounded-[2.5rem] bg-card/40 backdrop-blur-xl text-center relative overflow-hidden group transition-all hover:border-primary/50 hover:shadow-[0_0_40px_rgba(var(--primary-rgb),0.1)]">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(var(--primary-rgb),0.08),_transparent_60%)] pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
          <Sparkles className="h-14 w-14 mb-4 text-primary/40 group-hover:text-primary animate-bounce transition-colors" />
          <p className="text-3xl font-black text-foreground mb-2 drop-shadow-sm">مساحة العمل فارغة</p>
          <p className="text-lg text-muted-foreground font-medium">ابدأ بإضافة قسم جديد لبناء واجهتك السيادية</p>
        </div>
      ) : (
        <SortableContext
          items={pageStructure.sections.map((s) => `section-${s.id}`)}
          strategy={verticalListSortingStrategy}
        >
          {pageStructure.sections.map((section, index) => (
            <SortableSection key={`section-${section.id}`} section={section} index={index} />
          ))}
        </SortableContext>
      )}

      {/* 🟢 3. زر الإضافة الزجاجي (Glassmorphic Button) */}
      <Button
        variant="outline"
        className="w-full border-dashed border-2 py-10 rounded-[2rem] bg-card/40 backdrop-blur-2xl border-white/10 text-muted-foreground hover:text-primary hover:border-primary/50 hover:bg-primary/10 hover:shadow-[0_0_40px_rgba(var(--primary-rgb),0.25)] transition-all duration-300 group mt-8"
        onClick={() => {
          const newSection: Section = {
            id: crypto.randomUUID(),
            name: "قسم جديد",
            layout: "full-width",
            components: [],
          };
          addSection(newSection);
        }}
      >
        <Plus className="ml-3 h-7 w-7 group-hover:scale-125 group-hover:rotate-90 transition-transform duration-500" />
        <span className="font-black text-xl tracking-wide">إضافة قسم جديد (Section)</span>
      </Button>
    </div>
  );
}