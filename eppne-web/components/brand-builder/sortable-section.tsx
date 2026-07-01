// components/brand-builder/sortable-section.tsx
"use client";

import { useSortable, SortableContext, rectSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Section, useBrandBuilderStore } from "@/store/brand-builder-store";
import { SortableComponent } from "./sortable-component"; // 🟢 الترقية: استخدام المكون القابل للسحب بدلاً من المصيّر المباشر
import { GripHorizontal, Trash2, LayoutTemplate } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface SortableSectionProps {
  section: Section;
  index: number;
}

export function SortableSection({ section }: SortableSectionProps) {
  const { removeSection, updateSectionLayout } = useBrandBuilderStore();
  
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `section-${section.id}`,
    data: { type: "section", sectionId: section.id },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 100 : 1, // إبقاء القسم المسحوب فوق الجميع
  };

  // 🟢 هندسة الحاويات السيادية (CSS Grid / Bento)
  const layoutClass = 
    section.layout === "grid" ? "grid grid-cols-1 md:grid-cols-2 gap-6" :
    section.layout === "bento" ? "grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6 auto-rows-min md:auto-rows-[280px]" :
    "flex flex-col gap-6";

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`relative p-6 mb-8 rounded-[2.5rem] transition-all duration-500 group/section ${
        isDragging 
          ? "opacity-60 border-2 border-primary border-dashed shadow-[0_0_50px_rgba(var(--primary-rgb),0.3)] bg-primary/5 scale-[0.98]" 
          : "bg-card/30 backdrop-blur-xl border border-white/10 shadow-lg hover:border-primary/30 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.1)]"
      }`}
    >
      {/* 🟢 شريط أدوات القسم (Floating Glass Toolbar) */}
      <div className="absolute top-0 right-1/2 translate-x-1/2 -mt-5 opacity-0 group-hover/section:opacity-100 focus-within:opacity-100 transition-all duration-300 z-50">
        <div className="bg-background/80 backdrop-blur-2xl border border-white/10 shadow-[0_0_30px_rgba(var(--primary-rgb),0.2)] rounded-full px-4 py-1.5 flex items-center gap-3">
          <div {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing p-1.5 hover:bg-primary/20 hover:text-primary rounded-full text-muted-foreground transition-colors">
            <GripHorizontal className="h-5 w-5" />
          </div>
          <span className="text-sm font-black text-primary px-3 border-l border-white/10 tracking-widest">{section.name || "قسم سيادي"}</span>
          
          {/* مبدل المعمارية */}
          <Select value={section.layout} onValueChange={(v) => updateSectionLayout(section.id, v)}>
            <SelectTrigger className="h-8 w-32 text-xs font-bold border-0 bg-transparent focus:ring-0 shadow-none hover:text-primary transition-colors">
               <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-xl border-white/10 backdrop-blur-2xl bg-card/90">
               <SelectItem value="full-width" className="font-bold">عرض كامل</SelectItem>
               <SelectItem value="grid" className="font-bold">شبكة تقليدية</SelectItem>
               <SelectItem value="bento" className="font-bold text-primary">شبكة بينتو 🍱</SelectItem>
            </SelectContent>
          </Select>

          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:bg-destructive hover:text-white rounded-full border-r border-white/10 ml-1 transition-colors" onClick={() => removeSection(section.id)}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className={`min-h-[150px] w-full mt-2 transition-all duration-500 ${section.components.length === 0 ? "border-2 border-dashed border-primary/20 flex flex-col items-center justify-center bg-background/40 rounded-3xl group-hover/section:border-primary/50 group-hover/section:bg-primary/5" : layoutClass}`}>
        {section.components.length === 0 ? (
          <div className="text-center text-muted-foreground animate-in fade-in zoom-in duration-500">
            <LayoutTemplate className="h-12 w-12 mx-auto mb-3 text-primary/30 group-hover/section:text-primary/70 transition-colors group-hover/section:animate-bounce" />
            <p className="text-lg font-black text-foreground drop-shadow-sm">أفلت المكونات هنا لبناء الإمبراطورية</p>
            <p className="text-sm font-medium opacity-60">مساحة القسم جاهزة للاستقبال</p>
          </div>
        ) : (
          /* 🟢 تغليف المكونات بـ SortableContext لتفعيل السحب الداخلي الحر (بما في ذلك نظام بينتو) */
          <SortableContext items={section.components.map((c) => c.id)} strategy={rectSortingStrategy}>
            {section.components.map((comp, index) => (
               <SortableComponent key={comp.id} component={comp} sectionId={section.id} index={index} />
            ))}
          </SortableContext>
        )}
      </div>
    </div>
  );
}