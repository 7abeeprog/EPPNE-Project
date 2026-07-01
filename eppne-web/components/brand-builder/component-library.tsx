// components/brand-builder/component-library.tsx
"use client";

import { useDraggable } from "@dnd-kit/core";
import { Layout, Image, List, Star, DollarSign, Mail, Grid, FileText, GripVertical } from "lucide-react";

interface DraggableComponentProps {
  type: string;
  name: string;
  icon: React.ReactNode;
  defaultProps: Record<string, any>;
}

const components: DraggableComponentProps[] = [
  {
    type: "hero",
    name: "القسم الرئيسي (Hero)",
    icon: <Layout className="h-5 w-5 text-primary" />,
    defaultProps: {
      title: "مرحباً بكم في {entity_name}",
      subtitle: "نحن نقدم حلولاً مبتكرة",
      buttonText: "تواصل معنا",
      buttonLink: "/contact",
      backgroundImage: "",
    },
  },
  {
    type: "services",
    name: "الخدمات",
    icon: <Grid className="h-5 w-5 text-blue-500" />,
    defaultProps: {
      title: "خدماتنا",
      services: [
        { title: "خدمة 1", description: "وصف الخدمة 1", icon: "" },
        { title: "خدمة 2", description: "وصف الخدمة 2", icon: "" },
      ],
    },
  },
  {
    type: "features",
    name: "الميزات",
    icon: <List className="h-5 w-5 text-amber-500" />,
    defaultProps: {
      title: "الميزات",
      features: [
        { title: "ميزة 1", description: "وصف الميزة 1" },
        { title: "ميزة 2", description: "وصف الميزة 2" },
      ],
    },
  },
  {
    type: "testimonials",
    name: "آراء العملاء",
    icon: <Star className="h-5 w-5 text-yellow-400" />,
    defaultProps: {
      title: "آراء عملائنا",
      testimonials: [
        { text: "تجربة رائعة!", author: "أحمد", position: "مدير" },
      ],
    },
  },
  {
    type: "pricing",
    name: "خطط الأسعار",
    icon: <DollarSign className="h-5 w-5 text-emerald-500" />,
    defaultProps: {
      title: "خطط الأسعار",
      plans: [
        { name: "أساسي", price: "99", features: ["ميزة 1", "ميزة 2"] },
        { name: "متقدم", price: "199", features: ["ميزة 1", "ميزة 2", "ميزة 3"] },
      ],
    },
  },
  {
    type: "contact",
    name: "نموذج الاتصال",
    icon: <Mail className="h-5 w-5 text-rose-500" />,
    defaultProps: {
      title: "تواصل معنا",
      email: "info@eppne.com",
      phone: "+123456789",
      address: "العنوان هنا",
    },
  },
  {
    type: "gallery",
    name: "معرض الصور",
    icon: <Image className="h-5 w-5 text-indigo-500" />,
    defaultProps: {
      title: "معرض الأعمال",
      images: [
        { url: "https://via.placeholder.com/300", caption: "صورة 1" },
        { url: "https://via.placeholder.com/300", caption: "صورة 2" },
      ],
    },
  },
  {
    type: "text",
    name: "نص حر",
    icon: <FileText className="h-5 w-5 text-gray-500" />,
    defaultProps: {
      content: "نص يمكن تنسيقه...",
    },
  },
];

function DraggableComponentItem({ type, name, icon, defaultProps }: DraggableComponentProps) {
  // 🟢 العنصر الأصلي لا يتحرك (بدون transform)، الشبح (DragOverlay) هو من يتولى المهمة
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `new-${type}`,
    data: {
      type: "new-component",
      componentType: type,
      defaultProps,
    },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`p-4 rounded-2xl cursor-grab transition-all duration-300 flex items-center justify-between border ${
        isDragging 
          ? "opacity-40 bg-primary/10 border-dashed border-primary/50 shadow-inner scale-95" 
          : "bg-card/40 backdrop-blur-xl border-white/10 hover:border-primary/40 hover:shadow-[0_0_25px_rgba(var(--primary-rgb),0.15)] hover:-translate-y-0.5 group"
      }`}
    >
      <div className="flex items-center gap-4">
        <div className={`p-2 rounded-xl border border-white/5 shadow-inner transition-colors ${isDragging ? 'bg-transparent' : 'bg-background/50 group-hover:bg-primary/10 group-hover:border-primary/20'}`}>
          {icon}
        </div>
        <span className={`text-sm font-bold transition-colors ${isDragging ? 'text-muted-foreground' : 'text-foreground group-hover:text-primary'}`}>
          {name}
        </span>
      </div>
      <GripVertical className={`h-5 w-5 transition-opacity ${isDragging ? 'opacity-20' : 'text-muted-foreground/50 group-hover:text-primary/70 group-hover:opacity-100'}`} />
    </div>
  );
}

export function ComponentLibrary() {
  return (
    <div className="space-y-4 pb-8 pr-2">
      <div className="mb-6">
        <h3 className="text-sm font-black tracking-widest text-muted-foreground uppercase mb-1">الترسانة السيادية</h3>
        <p className="text-xs font-medium text-muted-foreground/70">اسحب المكونات وأفلتها في مساحة العمل</p>
      </div>
      {components.map((comp) => (
        <DraggableComponentItem key={comp.type} {...comp} />
      ))}
    </div>
  );
}