// components/entities/entity-brand-settings.tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SovereignEntity } from "@/types/entity";
import { Palette, Image as ImageIcon, Link as LinkIcon, Paintbrush, Sparkles, CheckCircle2 } from "lucide-react";
import { useEntityMutations } from "@/hooks/use-entities";

export function EntityBrandSettings({ entity }: { entity: SovereignEntity }) {
  const { updateEntity } = useEntityMutations(entity.id);

  const [logoUrl, setLogoUrl] = useState(entity.logo_url || "");
  const [coverUrl, setCoverUrl] = useState(entity.cover_image_url || "");
  const [primaryColor, setPrimaryColor] = useState(entity.primary_color || "#8CC63F");
  const [secondaryColor, setSecondaryColor] = useState(entity.secondary_color || "#06b6d4");

  const handleSave = () => {
    // 🟢 الحل الجراحي: استخدام undefined بدلاً من null ليرضى TypeScript
    updateEntity.mutate({
      logo_url: logoUrl || undefined,
      cover_image_url: coverUrl || undefined,
      primary_color: primaryColor,
      secondary_color: secondaryColor,
    });
  };

  return (
    <div className="w-full rounded-[2rem] border border-white/10 bg-card/30 backdrop-blur-xl shadow-lg relative overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="absolute top-0 right-0 w-72 h-72 blur-[100px] rounded-full pointer-events-none opacity-20 transition-colors duration-500" style={{ backgroundColor: primaryColor }} />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 md:p-8 border-b border-white/5 bg-background/20 relative z-10">
        <div>
          <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
            <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20 shadow-inner">
              <Palette className="h-6 w-6 text-primary" />
            </div>
            الهوية البصرية
          </h2>
          <p className="mt-2 text-sm text-muted-foreground font-medium">
            تخصيص مظهر صفحة الكيان العامة وألوانها السيادية
          </p>
        </div>
      </div>

      <div className="p-6 md:p-8 space-y-8 relative z-10">
        
        {/* قسم الروابط والصور */}
        <div className="grid gap-8 md:grid-cols-2">
          <div className="space-y-3 p-5 rounded-2xl bg-background/40 border border-white/5 shadow-inner group transition-colors hover:border-primary/30">
            <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <ImageIcon className="h-4 w-4 text-primary/70" /> رابط الشعار (Logo)
            </Label>
            <div className="relative">
              <LinkIcon className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="https://..."
                value={logoUrl}
                onChange={(e) => setLogoUrl(e.target.value)}
                className="pl-3 pr-9 bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-12"
              />
            </div>
            {logoUrl && (
              <div className="mt-3 p-4 border border-white/5 rounded-xl bg-card/50 flex items-center justify-center">
                <img src={logoUrl} alt="Logo preview" className="max-h-20 object-contain drop-shadow-md" />
              </div>
            )}
          </div>

          <div className="space-y-3 p-5 rounded-2xl bg-background/40 border border-white/5 shadow-inner group transition-colors hover:border-primary/30">
            <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <ImageIcon className="h-4 w-4 text-primary/70" /> رابط الغلاف (Cover)
            </Label>
            <div className="relative">
              <LinkIcon className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="https://..."
                value={coverUrl}
                onChange={(e) => setCoverUrl(e.target.value)}
                className="pl-3 pr-9 bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-12"
              />
            </div>
            {coverUrl && (
              <div className="mt-3 p-1 border border-white/5 rounded-xl bg-card/50 overflow-hidden">
                <img src={coverUrl} alt="Cover preview" className="w-full h-24 object-cover rounded-lg" />
              </div>
            )}
          </div>
        </div>

        {/* قسم الألوان */}
        <div className="p-6 rounded-2xl bg-background/40 border border-white/5 shadow-inner space-y-6">
          <h4 className="text-sm font-black text-foreground flex items-center gap-2 border-b border-white/5 pb-3">
            <Paintbrush className="h-4 w-4 text-primary" /> لوحة الألوان السيادية
          </h4>
          
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-3">
              <Label className="text-xs font-bold text-muted-foreground">اللون الأساسي (Primary)</Label>
              <div className="flex gap-3 items-center border border-white/10 bg-background/50 p-2 rounded-xl">
                <Input type="color" value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} className="w-12 h-12 p-0 border-0 rounded-lg cursor-pointer shadow-md" />
                <Input value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} className="flex-1 bg-transparent border-0 font-mono font-bold focus-visible:ring-0" />
              </div>
            </div>
            
            <div className="space-y-3">
              <Label className="text-xs font-bold text-muted-foreground">اللون الثانوي (Secondary)</Label>
              <div className="flex gap-3 items-center border border-white/10 bg-background/50 p-2 rounded-xl">
                <Input type="color" value={secondaryColor} onChange={(e) => setSecondaryColor(e.target.value)} className="w-12 h-12 p-0 border-0 rounded-lg cursor-pointer shadow-md" />
                <Input value={secondaryColor} onChange={(e) => setSecondaryColor(e.target.value)} className="flex-1 bg-transparent border-0 font-mono font-bold focus-visible:ring-0" />
              </div>
            </div>
          </div>
        </div>

        {/* المعاينة الحية */}
        <div className="space-y-3">
          <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2 px-2">
            <Sparkles className="h-4 w-4 text-primary/70" /> معاينة حية للألوان
          </Label>
          <div 
            className="rounded-2xl p-8 relative overflow-hidden shadow-inner border transition-colors duration-500" 
            style={{ backgroundColor: primaryColor + "10", borderColor: secondaryColor + "40" }}
          >
            <div className="absolute top-0 right-0 w-full h-full opacity-20 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-current to-transparent pointer-events-none" style={{ color: primaryColor }} />
            
            <div className="relative z-10 space-y-3 max-w-sm">
              <h3 className="font-black text-2xl drop-shadow-sm transition-colors duration-500" style={{ color: primaryColor }}>
                عنوان سيادي تجريبي
              </h3>
              <p className="text-sm font-medium transition-colors duration-500" style={{ color: secondaryColor }}>
                هذا النص يوضح كيف سيبدو اللون الثانوي الخاص بكيانك عند دمجه مع اللون الأساسي في الواجهات الزجاجية.
              </p>
              <div className="pt-2">
                <Button className="rounded-xl shadow-lg font-bold transition-colors duration-500" style={{ backgroundColor: primaryColor, color: '#fff' }}>
                  زر إجراء تفاعلي
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* زر الحفظ */}
        <div className="pt-4 flex justify-end">
          <Button 
            onClick={handleSave} 
            disabled={updateEntity.isPending} 
            size="lg"
            className="w-full md:w-auto rounded-xl px-10 font-black shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-all text-lg h-14"
          >
            {updateEntity.isPending ? (
              <span className="flex items-center gap-2"><Sparkles className="h-5 w-5 animate-spin-slow" /> جاري التشفير والحفظ...</span>
            ) : (
              <span className="flex items-center gap-2"><CheckCircle2 className="h-5 w-5" /> اعتماد الهوية البصرية</span>
            )}
          </Button>
        </div>

      </div>
    </div>
  );
}