// components/brand-builder/component-renderer.tsx
"use client";

import { Component, useBrandBuilderStore } from "@/store/brand-builder-store";
import { Button } from "@/components/ui/button";
import { Trash2, Settings, Code, Zap } from "lucide-react";
import { motion } from "framer-motion";

interface Props {
  component: Component;
  sectionId?: string;
  isPreviewMode?: boolean;
}

export function ComponentRenderer({ component, sectionId, isPreviewMode = false }: Props) {
  const { selectedComponentId, setSelectedComponent, removeComponent } = useBrandBuilderStore();
  const isSelected = !isPreviewMode && selectedComponentId === component.id;

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation(); // منع انتقال النقرة لتحديد المكون أثناء حذفه
    if (sectionId) removeComponent(sectionId, component.id);
  };

  const { 
    bgColor, textColor, rounded, isGlass, hasNeon, neonColor,
    paddingTop = 4, paddingBottom = 4, paddingRight = 4, paddingLeft = 4,
    fontWeight = "normal", letterSpacing = "normal",
    bentoSpan = "1x1" 
  } = component.props;

  // 🟢 هندسة شبكة بينتو (Bento Grid)
  const bentoClass = 
    bentoSpan === "2x1" ? "md:col-span-2" :
    bentoSpan === "1x2" ? "row-span-2" :
    bentoSpan === "2x2" ? "md:col-span-2 row-span-2" :
    bentoSpan === "full" ? "md:col-span-full" :
    "col-span-1";

  // 🟢 تطبيق الأنماط الديناميكية السيادية
  const dynamicStyles = {
    backgroundColor: isGlass ? "transparent" : (bgColor || "transparent"),
    color: textColor || "inherit",
    paddingTop: `${paddingTop}rem`,
    paddingBottom: `${paddingBottom}rem`,
    paddingRight: `${paddingRight}rem`,
    paddingLeft: `${paddingLeft}rem`,
    borderRadius: `${rounded !== undefined ? rounded : 24}px`, // افتراضي سيادي: 24px
    fontWeight: fontWeight,
  };

  const trackingClass = letterSpacing === "tighter" ? "tracking-tighter" : letterSpacing === "widest" ? "tracking-widest" : "tracking-normal";
  
  // 🟢 تفعيل الدروع الزجاجية
  const glassClass = isGlass ? "backdrop-blur-2xl bg-card/40 border border-white/10 shadow-[0_8px_32px_0_rgba(var(--primary-rgb),0.1)]" : "";
  const neonClass = hasNeon ? "relative overflow-hidden" : "relative"; 
  const combinedClasses = `h-full w-full ${glassClass} ${neonClass} ${trackingClass}`;

  // 🟢 إعدادات الفيزياء المتقدمة (Framer Motion)
  const physicsSettings = {
    initial: { opacity: 0, y: 30, scale: 0.98 },
    whileInView: { opacity: 1, y: 0, scale: 1 },
    viewport: { once: true, margin: "-50px" },
    transition: { type: "spring", stiffness: 300, damping: 25, mass: 0.8 } as any  
  };

  const hoverPhysics = isPreviewMode ? {
    whileHover: { scale: 1.01, y: -2, transition: { duration: 0.2 } },
    whileTap: { scale: 0.99 }
  } : {};

  // 🟢 دالة تصيير المحتوى الداخلي بناءً على نوع المكون
  const renderLiveContent = () => {
    switch (component.type) {
      case "hero":
        return (
          <div style={dynamicStyles} className={`${combinedClasses} flex flex-col items-center justify-center text-center group/hero z-10`}>
            {hasNeon && (
              <motion.div 
                animate={{ opacity: [0.15, 0.3, 0.15], scale: [1, 1.1, 1] }}
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full blur-[120px] rounded-full pointer-events-none -z-10"
                style={{ backgroundColor: neonColor || 'var(--primary)' }}
              />
            )}
            
            <div className="relative z-20 max-w-4xl space-y-6">
              <h1 className="text-4xl md:text-6xl lg:text-7xl font-black drop-shadow-md bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70" style={{ fontWeight }}>
                {component.props.title}
              </h1>
              <p className="text-lg md:text-2xl text-muted-foreground leading-relaxed max-w-2xl mx-auto font-medium">
                {component.props.subtitle}
              </p>
              {component.props.buttonText && (
                <div className="pt-6">
                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="inline-block">
                    <Button size="lg" className="h-14 px-10 text-lg font-black shadow-2xl transition-all duration-300 rounded-2xl" style={{ backgroundColor: hasNeon ? neonColor : undefined }}>
                      <Zap className="mr-2 h-5 w-5" /> {component.props.buttonText}
                    </Button>
                  </motion.div>
                </div>
              )}
            </div>
          </div>
        );

      case "text":
        return (
          <div style={dynamicStyles} className={`${combinedClasses} flex items-center`}>
            <p className="text-lg md:text-xl leading-loose whitespace-pre-wrap font-medium">
              {component.props.content}
            </p>
          </div>
        );

      default:
        return (
          <div style={dynamicStyles} className={`${combinedClasses} flex flex-col items-center justify-center text-center border-2 border-dashed border-primary/20 bg-background/50`}>
             <Code className="h-12 w-12 text-primary/40 mb-4" />
             <span className="font-mono text-xs font-black opacity-80 mb-3 uppercase tracking-widest px-4 py-1.5 rounded-full bg-primary/10 text-primary border border-primary/20">
               {component.type}
             </span>
             <h3 className="text-2xl font-black text-foreground/50">{component.props.title || "مكون قيد الإنشاء"}</h3>
          </div>
        );
    }
  };

  // 🟢 1. العرض للجمهور (Preview Mode)
  if (isPreviewMode) return (
    <motion.div 
      className={`w-full h-full ${bentoClass}`}
      {...physicsSettings}
      {...hoverPhysics}
    >
      {renderLiveContent()}
    </motion.div>
  );

  // 🟢 2. العرض للمطور (Builder Mode)
  return (
    <motion.div 
      layout // تنعيم الحركة عند تغيير أبعاد الـ Bento
      {...physicsSettings}
      onClick={() => setSelectedComponent(component.id)}
      className={`relative group cursor-pointer transition-all duration-300 ${bentoClass} ${
        isSelected 
          ? "ring-2 ring-primary ring-offset-4 ring-offset-background shadow-[0_0_40px_rgba(var(--primary-rgb),0.3)] z-20" 
          : "hover:ring-2 hover:ring-primary/30 hover:ring-offset-2 hover:ring-offset-background z-10"
      }`}
      style={{ borderRadius: `${rounded !== undefined ? rounded : 24}px` }}
    >
      {/* أدوات التحكم العائمة الزجاجية */}
      {sectionId && (
        <div className={`absolute top-4 left-4 flex gap-2 transition-all duration-300 z-50 ${isSelected ? "opacity-100 translate-y-0 scale-100" : "opacity-0 -translate-y-4 scale-90 group-hover:opacity-100 group-hover:translate-y-0 group-hover:scale-100"}`}>
          <Button variant="secondary" size="icon" className="h-10 w-10 rounded-full shadow-[0_0_20px_rgba(0,0,0,0.2)] bg-background/80 backdrop-blur-xl border border-white/10 hover:bg-background hover:scale-110 transition-all">
            <Settings className="h-5 w-5 text-primary" />
          </Button>
          <Button variant="destructive" size="icon" className="h-10 w-10 rounded-full shadow-[0_0_20px_rgba(220,38,38,0.2)] bg-destructive/90 backdrop-blur-xl border border-destructive/20 hover:bg-destructive hover:scale-110 transition-all" onClick={handleDelete}>
            <Trash2 className="h-5 w-5 text-white" />
          </Button>
        </div>
      )}

      {/* منع التفاعل الداخلي ليتمكن المدير من سحب أو تحديد العنصر */}
      <div className="w-full h-full pointer-events-none">
        {renderLiveContent()}
      </div>
    </motion.div>
  );
}