// app/(dashboard)/entities/[id]/brand-builder/page.tsx
"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useBrandBuilderStore } from "@/store/brand-builder-store";
import { ComponentLibrary } from "@/components/brand-builder/component-library";
import { Canvas } from "@/components/brand-builder/canvas";
import { PropertyEditor } from "@/components/brand-builder/property-editor";
import { ComponentRenderer } from "@/components/brand-builder/component-renderer";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Save, Eye, Code, GripVertical, LayoutGrid, Zap } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { DndContext, DragEndEvent, closestCenter, DragStartEvent, DragOverlay, useSensor, useSensors, MouseSensor, TouchSensor } from "@dnd-kit/core";
import { arrayMove } from "@dnd-kit/sortable";

export default function BrandBuilderPage() {
  const params = useParams();
  const entityId = parseInt(params.id as string);
  const { fetchPageStructure, savePageStructure, pageStructure, isLoading } = useBrandBuilderStore();
  
  const [activeTab, setActiveTab] = useState("editor");
  const [isSaving, setIsSaving] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeDragData, setActiveDragData] = useState<any>(null);

  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 5 } })
  );

  useEffect(() => {
    fetchPageStructure(entityId);
  }, [entityId, fetchPageStructure]);

  // ... [باقي دوال handleSave و handleDragEnd كما هي لضمان استقرار المنطق] ...

  return (
    <div className="h-screen flex flex-col bg-background/50 backdrop-blur-sm">
      
      {/* 🟢 ترويسة سيادية زجاجية */}
      <header className="border-b border-white/10 p-4 flex items-center justify-between bg-card/50 backdrop-blur-xl shadow-lg sticky top-0 z-40">
        <div className="flex items-center gap-4">
          <Link href={`/entities/${entityId}`}>
            <Button variant="ghost" size="icon" className="rounded-full hover:bg-primary/10"><ArrowLeft className="h-5 w-5" /></Button>
          </Link>
          <div className="flex items-center gap-3">
             <div className="p-2 bg-primary/10 rounded-xl border border-primary/20"><Zap className="h-5 w-5 text-primary" /></div>
             <h1 className="text-lg font-black tracking-tight">استوديو البناء السيادي</h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="rounded-xl border-white/10 bg-transparent hover:bg-white/5"><Eye className="ml-2 h-4 w-4" /> معاينة</Button>
          <Button onClick={handleSave} disabled={isSaving} className="rounded-xl bg-primary hover:bg-primary/90 font-bold shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)]">
            <Save className="ml-2 h-4 w-4" /> {isSaving ? "جاري الحفظ..." : "حفظ الهيكل"}
          </Button>
        </div>
      </header>

      {/* 🟢 مساحة العمل الزجاجية */}
      <main className="flex-1 overflow-hidden p-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
          <TabsList className="bg-card/50 border border-white/5 p-1 rounded-2xl w-fit mb-6">
            <TabsTrigger value="editor" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><Code className="ml-2 h-4 w-4" /> المحرر</TabsTrigger>
            <TabsTrigger value="preview" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><Eye className="ml-2 h-4 w-4" /> المعاينة</TabsTrigger>
          </TabsList>

          <TabsContent value="editor" className="flex-1 overflow-hidden m-0">
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
              <div className="flex h-full gap-6">
                {/* 🟢 لوحات جانبية زجاجية */}
                <div className="w-80 bg-card/30 backdrop-blur-xl border border-white/5 rounded-3xl p-4 shadow-xl"><ComponentLibrary /></div>
                
                <div className="flex-1 bg-card/20 backdrop-blur-lg border border-white/5 rounded-3xl p-6 shadow-inner overflow-y-auto custom-scrollbar">
                  <Canvas />
                </div>
                
                <div className="w-80 bg-card/30 backdrop-blur-xl border border-white/5 rounded-3xl p-4 shadow-xl"><PropertyEditor /></div>
              </div>

              {/* 🟢 DragOverlay مطور بأسلوب النيون */}
              <DragOverlay dropAnimation={null}>
                {activeId ? (
                  <div className="p-4 border border-primary/30 rounded-2xl bg-background/80 backdrop-blur-2xl shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] flex items-center gap-3">
                    <LayoutGrid className="h-5 w-5 text-primary" />
                    <span className="font-bold text-foreground">{activeDragData?.name || "نقل العنصر..."}</span>
                  </div>
                ) : null}
              </DragOverlay>
            </DndContext>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}