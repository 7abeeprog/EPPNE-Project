// components/entities/entity-tabs.tsx
"use client";

import Link from "next/link";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Building2, Users, FileText, Palette, Settings, Layout, Sparkles, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EntityBasicInfo } from "./entity-basic-info";
import { EntityRepresentatives } from "./entity-representatives";
import { EntityDocuments } from "./entity-documents";
import { EntityBrandSettings } from "./entity-brand-settings";
import { SovereignEntity } from "@/types/entity";

interface EntityTabsProps {
  entity: SovereignEntity;
}

export function EntityTabs({ entity }: EntityTabsProps) {
  return (
    <Tabs defaultValue="basic" className="w-full block">
      {/* 🟢 لوحة تحكم زجاجية للتبويبات */}
      <TabsList className="flex flex-wrap h-auto w-full justify-start gap-2 p-2 bg-card/30 backdrop-blur-xl border border-white/10 rounded-2xl shadow-inner">
        <TabsTrigger 
          value="basic" 
          className="flex items-center gap-2 grow sm:grow-0 rounded-xl px-4 py-2.5 font-bold text-muted-foreground data-[state=active]:bg-primary/15 data-[state=active]:text-primary data-[state=active]:border data-[state=active]:border-primary/30 data-[state=active]:shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)] transition-all"
        >
          <Building2 className="h-4 w-4" />
          <span>معلومات أساسية</span>
        </TabsTrigger>
        
        <TabsTrigger 
          value="representatives" 
          className="flex items-center gap-2 grow sm:grow-0 rounded-xl px-4 py-2.5 font-bold text-muted-foreground data-[state=active]:bg-primary/15 data-[state=active]:text-primary data-[state=active]:border data-[state=active]:border-primary/30 data-[state=active]:shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)] transition-all"
        >
          <Users className="h-4 w-4" />
          <span>الممثلون</span>
        </TabsTrigger>
        
        <TabsTrigger 
          value="documents" 
          className="flex items-center gap-2 grow sm:grow-0 rounded-xl px-4 py-2.5 font-bold text-muted-foreground data-[state=active]:bg-primary/15 data-[state=active]:text-primary data-[state=active]:border data-[state=active]:border-primary/30 data-[state=active]:shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)] transition-all"
        >
          <FileText className="h-4 w-4" />
          <span>المستندات</span>
        </TabsTrigger>
        
        <TabsTrigger 
          value="branding" 
          className="flex items-center gap-2 grow sm:grow-0 rounded-xl px-4 py-2.5 font-bold text-muted-foreground data-[state=active]:bg-primary/15 data-[state=active]:text-primary data-[state=active]:border data-[state=active]:border-primary/30 data-[state=active]:shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)] transition-all"
        >
          <Palette className="h-4 w-4" />
          <span>الهوية البصرية</span>
        </TabsTrigger>
        
        <TabsTrigger 
          value="brand-builder" 
          className="flex items-center gap-2 grow sm:grow-0 rounded-xl px-4 py-2.5 font-bold text-muted-foreground data-[state=active]:bg-primary/15 data-[state=active]:text-primary data-[state=active]:border data-[state=active]:border-primary/30 data-[state=active]:shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)] transition-all"
        >
          <Layout className="h-4 w-4" />
          <span>محرر الواجهات</span>
        </TabsTrigger>
        
        <TabsTrigger 
          value="settings" 
          className="flex items-center gap-2 grow sm:grow-0 rounded-xl px-4 py-2.5 font-bold text-muted-foreground data-[state=active]:bg-primary/15 data-[state=active]:text-primary data-[state=active]:border data-[state=active]:border-primary/30 data-[state=active]:shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)] transition-all"
        >
          <Settings className="h-4 w-4" />
          <span>إعدادات</span>
        </TabsTrigger>
      </TabsList>

      {/* 🟢 قطاعات المحتوى المعززة بالحركة */}
      <TabsContent value="basic" className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <EntityBasicInfo entity={entity} />
      </TabsContent>

      <TabsContent value="representatives" className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <EntityRepresentatives entityId={entity.id} />
      </TabsContent>

      <TabsContent value="documents" className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <EntityDocuments entityId={entity.id} />
      </TabsContent>

      <TabsContent value="branding" className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <EntityBrandSettings entity={entity} />
      </TabsContent>

      {/* 🟢 بوابة محرر الصفحات السيادية */}
      <TabsContent value="brand-builder" className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="flex flex-col items-center justify-center py-20 px-4 rounded-[2rem] border border-white/10 bg-card/30 backdrop-blur-xl shadow-lg relative overflow-hidden group">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-primary/10 blur-[100px] rounded-full pointer-events-none transition-transform duration-700 group-hover:scale-150" />
          <div className="p-4 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner mb-6 relative z-10">
            <Layout className="h-12 w-12 text-primary" />
          </div>
          <h3 className="text-3xl font-black text-foreground mb-3 drop-shadow-md relative z-10">محرر الصفحات السيادي</h3>
          <p className="text-muted-foreground font-medium mb-8 max-w-md text-center relative z-10">
            انتقل إلى غرفة التحكم المعمارية لبناء وتخصيص الواجهة العامة للكيان باستخدام أحدث أدوات السحب والإفلات.
          </p>
          <Button asChild size="lg" className="rounded-2xl h-14 px-10 text-lg font-black shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-all relative z-10">
            <Link href={`/entities/${entity.id}/brand-builder`}>
              <Sparkles className="ml-2 h-5 w-5" />
              اقتحام محرر الواجهات
            </Link>
          </Button>
        </div>
      </TabsContent>

      {/* 🟢 قبو الإعدادات المتقدمة */}
      <TabsContent value="settings" className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="flex flex-col items-center justify-center py-20 px-4 rounded-[2rem] border border-dashed border-white/20 bg-background/30 backdrop-blur-md shadow-inner relative overflow-hidden">
          <Lock className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <h3 className="text-xl font-bold text-muted-foreground/70 mb-2">قبو الإعدادات المتقدمة</h3>
          <p className="text-sm font-medium text-muted-foreground/50">
            هذا القطاع يخضع للتطوير حالياً وسيتوفر في التحديثات القادمة.
          </p>
        </div>
      </TabsContent>
    </Tabs>
  );
}