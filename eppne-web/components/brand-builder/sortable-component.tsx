// components/brand-builder/sortable-component.tsx
"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Component } from "@/store/brand-builder-store";
import { ComponentRenderer } from "./component-renderer";
import { GripVertical } from "lucide-react";
import { useBrandBuilderStore } from "@/store/brand-builder-store";

interface SortableComponentProps {
  component: Component;
  sectionId: string;
  index: number;
}

export function SortableComponent({ component, sectionId, index }: SortableComponentProps) {
  const { selectedComponentId, setSelectedComponent } = useBrandBuilderStore();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: component.id });

  // 🟢 هندسة الحركة والتحولات
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 50 : 1, // إبقاء العنصر المسحوب فوق باقي العناصر
  };

  const isSelected = selectedComponentId === component.id;

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={(e) => {
        e.stopPropagation(); // منع تداخل النقرات مع الأقسام الأب
        setSelectedComponent(component.id);
      }}
      className={`relative group h-full transition-all duration-300 ${
        isDragging 
          ? "opacity-60 scale-95 shadow-[0_0_50px_rgba(var(--primary-rgb),0.3)] ring-2 ring-primary ring-dashed rounded-3xl" 
          : ""
      }`}
    >
      {/* 🟢 مقبض السحب الزجاجي السيادي (Drag Handle) */}
      <div 
        {...attributes} 
        {...listeners} 
        className={`absolute top-4 right-4 z-50 p-2 rounded-xl backdrop-blur-xl bg-background/80 border border-white/10 shadow-lg cursor-grab active:cursor-grabbing transition-all duration-300 ${
          isSelected ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2 group-hover:opacity-100 group-hover:translate-y-0"
        }`}
      >
        <GripVertical className="h-5 w-5 text-muted-foreground hover:text-primary transition-colors" />
      </div>

      {/* 🟢 المكون المصيّر (الذي يحتوي بداخله على أزرار الحذف والإعدادات السيادية التي برمجناها) */}
      <ComponentRenderer component={component} sectionId={sectionId} />
    </div>
  );
}