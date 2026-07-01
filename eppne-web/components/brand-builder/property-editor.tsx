// components/brand-builder/property-editor.tsx
"use client";

import { useBrandBuilderStore } from "@/store/brand-builder-store";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Settings2, Type, Link as LinkIcon, Image as ImageIcon, Paintbrush, LayoutPanelLeft, BoxSelect, LayoutGrid, Sparkles } from "lucide-react";

export function PropertyEditor() {
  const { pageStructure, selectedComponentId, updateComponentProps } = useBrandBuilderStore();

  let selectedComponent = null;
  let parentSectionId = null;

  if (pageStructure && selectedComponentId) {
    for (const section of pageStructure.sections) {
      const comp = section.components.find((c) => c.id === selectedComponentId);
      if (comp) {
        selectedComponent = comp;
        parentSectionId = section.id;
        break;
      }
    }
  }

  // 🟢 1. شاشة الانتظار الزجاجية (Empty State)
  if (!selectedComponent || !parentSectionId) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[400px] border border-white/10 rounded-[2rem] bg-card/30 backdrop-blur-xl shadow-inner space-y-6 p-8 animate-in fade-in duration-500">
        <div className="p-4 bg-muted/20 rounded-2xl border border-white/5 shadow-inner">
          <LayoutPanelLeft className="h-12 w-12 text-muted-foreground/50" />
        </div>
        <p className="text-sm md:text-base text-center font-medium text-muted-foreground leading-relaxed">
          قم بتحديد أي مكون في مساحة العمل <br />
          للسيطرة على محتواه وتصميمه بدقة سيادية.
        </p>
      </div>
    );
  }

  const { id, type, props } = selectedComponent;

  const handlePropChange = (key: string, value: any) => {
    updateComponentProps(parentSectionId!, id, { [key]: value });
  };

  // مصفوفة الخصائص التصميمية لكي لا تظهر في تبويب "المحتوى"
  const designPropsKeys = [
    "bgColor", "textColor", "rounded", "isGlass", "hasNeon", "neonColor",
    "paddingTop", "paddingBottom", "paddingRight", "paddingLeft",
    "fontWeight", "letterSpacing", "bentoSpan"
  ];

  return (
    <div className="space-y-6 h-full flex flex-col animate-in fade-in slide-in-from-right-4 duration-300">
      
      {/* 🟢 رأس لوحة التحكم */}
      <div className="bg-primary/10 text-primary px-4 py-3 rounded-2xl font-mono text-sm font-black uppercase tracking-wider flex items-center justify-between shadow-inner border border-primary/20">
        <div className="flex items-center gap-3">
          <Settings2 className="h-5 w-5 animate-spin-slow" />
          التحكم الجراحي
        </div>
        <span className="bg-primary/20 px-2 py-1 rounded-lg text-xs">{type}</span>
      </div>

      <Tabs defaultValue="design" className="flex-1 overflow-y-auto pr-2 custom-scrollbar pb-10">
        <TabsList className="grid w-full grid-cols-2 mb-6 bg-card/50 backdrop-blur-md p-1.5 rounded-2xl border border-white/10 shadow-inner">
          <TabsTrigger value="content" className="font-bold text-sm rounded-xl py-2 data-[state=active]:bg-background data-[state=active]:shadow-md transition-all">
            <Type className="h-4 w-4 ml-2" /> المحتوى
          </TabsTrigger>
          <TabsTrigger value="design" className="font-bold text-sm rounded-xl py-2 data-[state=active]:bg-background data-[state=active]:shadow-md transition-all">
            <Paintbrush className="h-4 w-4 ml-2" /> التصميم
          </TabsTrigger>
        </TabsList>

        {/* 🟢 تبويب المحتوى */}
        <TabsContent value="content" className="space-y-4">
          {Object.entries(props).map(([key, value]) => {
            if (Array.isArray(value) || designPropsKeys.includes(key)) return null;

            return (
              <div key={key} className="space-y-3 bg-card/40 backdrop-blur-md p-4 rounded-2xl border border-white/10 shadow-inner hover:border-primary/30 transition-colors group">
                <Label className="capitalize text-xs font-bold text-muted-foreground group-hover:text-primary transition-colors flex items-center gap-2">
                  {key.includes('title') ? <Type className="h-4 w-4"/> :
                   key.includes('image') ? <ImageIcon className="h-4 w-4"/> :
                   key.includes('link') ? <LinkIcon className="h-4 w-4"/> :
                   <Settings2 className="h-4 w-4" />}
                  {key === 'title' ? 'العنوان الرئيسي' : 
                   key === 'subtitle' ? 'النص الفرعي' : 
                   key === 'buttonText' ? 'نص الإجراء (الزر)' : 
                   key === 'content' ? 'المحتوى' : key}
                </Label>

                {key === 'content' || key === 'subtitle' || key === 'description' ? (
                  <Textarea
                    value={value as string}
                    onChange={(e) => handlePropChange(key, e.target.value)}
                    className="resize-none h-28 bg-background/50 focus-visible:ring-primary border-white/5 rounded-xl shadow-inner text-sm"
                  />
                ) : (
                  <Input
                    value={value as string}
                    onChange={(e) => handlePropChange(key, e.target.value)}
                    className="bg-background/50 focus-visible:ring-primary border-white/5 rounded-xl shadow-inner h-12"
                  />
                )}
              </div>
            );
          })}
        </TabsContent>

        {/* 🟢 تبويب التصميم (السيطرة المتقدمة) */}
        <TabsContent value="design" className="space-y-5">
          
          {/* هندسة بينتو */}
          <div className="space-y-4 bg-card/40 backdrop-blur-md p-5 rounded-2xl border border-white/10 shadow-inner">
            <h4 className="text-sm font-black text-foreground mb-2 flex items-center gap-2 border-b border-border/50 pb-3">
              <div className="p-1.5 bg-primary/10 rounded-lg"><LayoutGrid className="h-4 w-4 text-primary" /></div>
              هندسة بينتو (Bento Span)
            </h4>
            <div className="flex items-center justify-between pt-2">
              <Label className="text-xs font-bold text-muted-foreground">حجم الصندوق الداخلي</Label>
              <Select value={props.bentoSpan || "1x1"} onValueChange={(v) => handlePropChange('bentoSpan', v)}>
                <SelectTrigger className="w-[140px] h-10 text-xs font-bold bg-background/50 border-white/5 rounded-xl">
                  <SelectValue placeholder="اختر الحجم" />
                </SelectTrigger>
                <SelectContent className="rounded-xl border-white/10 backdrop-blur-2xl bg-card/90">
                  <SelectItem value="1x1">عادي (1x1)</SelectItem>
                  <SelectItem value="2x1">عريض (2x1)</SelectItem>
                  <SelectItem value="1x2">طويل (1x2)</SelectItem>
                  <SelectItem value="2x2">ضخم (2x2)</SelectItem>
                  <SelectItem value="full">عرض كامل</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* الألوان */}
          <div className="space-y-4 bg-card/40 backdrop-blur-md p-5 rounded-2xl border border-white/10 shadow-inner">
            <h4 className="text-sm font-black text-foreground mb-2 flex items-center gap-2 border-b border-border/50 pb-3">
              <div className="p-1.5 bg-primary/10 rounded-lg"><Paintbrush className="h-4 w-4 text-primary" /></div>
              الألوان الأساسية
            </h4>
            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="space-y-3">
                <Label className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">خلفية المكون</Label>
                <div className="flex items-center gap-3 border border-white/5 rounded-xl p-2 bg-background/50 shadow-inner">
                  <Input type="color" value={props.bgColor || "#ffffff"} onChange={(e) => handlePropChange('bgColor', e.target.value)} className="w-8 h-8 p-0 border-0 rounded-lg cursor-pointer" />
                  <span className="text-xs font-mono font-medium">{props.bgColor || 'شفاف'}</span>
                </div>
              </div>
              <div className="space-y-3">
                <Label className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">لون النصوص</Label>
                <div className="flex items-center gap-3 border border-white/5 rounded-xl p-2 bg-background/50 shadow-inner">
                  <Input type="color" value={props.textColor || "#000000"} onChange={(e) => handlePropChange('textColor', e.target.value)} className="w-8 h-8 p-0 border-0 rounded-lg cursor-pointer" />
                  <span className="text-xs font-mono font-medium">{props.textColor || 'افتراضي'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* التايبوجرافي */}
          <div className="space-y-4 bg-card/40 backdrop-blur-md p-5 rounded-2xl border border-white/10 shadow-inner">
            <h4 className="text-sm font-black text-foreground mb-2 flex items-center gap-2 border-b border-border/50 pb-3">
              <div className="p-1.5 bg-primary/10 rounded-lg"><Type className="h-4 w-4 text-primary" /></div>
              التايبوجرافي (النصوص)
            </h4>
            <div className="space-y-4 pt-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-bold text-muted-foreground">وزن الخط (Weight)</Label>
                <Select value={props.fontWeight || "normal"} onValueChange={(v) => handlePropChange('fontWeight', v)}>
                  <SelectTrigger className="w-[140px] h-10 text-xs font-bold bg-background/50 border-white/5 rounded-xl">
                    <SelectValue placeholder="اختر الوزن" />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl border-white/10 backdrop-blur-2xl bg-card/90">
                    <SelectItem value="light">خفيف (Light)</SelectItem>
                    <SelectItem value="normal">عادي (Normal)</SelectItem>
                    <SelectItem value="bold">عريض (Bold)</SelectItem>
                    <SelectItem value="800">أسود (Extra Bold)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <Label className="text-xs font-bold text-muted-foreground">تباعد الأحرف (Tracking)</Label>
                <Select value={props.letterSpacing || "normal"} onValueChange={(v) => handlePropChange('letterSpacing', v)}>
                  <SelectTrigger className="w-[140px] h-10 text-xs font-bold bg-background/50 border-white/5 rounded-xl">
                    <SelectValue placeholder="اختر التباعد" />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl border-white/10 backdrop-blur-2xl bg-card/90">
                    <SelectItem value="tighter">مضغوط</SelectItem>
                    <SelectItem value="normal">طبيعي</SelectItem>
                    <SelectItem value="widest">واسع جداً</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* المسافات الرباعية */}
          <div className="space-y-4 bg-card/40 backdrop-blur-md p-5 rounded-2xl border border-white/10 shadow-inner">
            <h4 className="text-sm font-black text-foreground mb-2 flex items-center gap-2 border-b border-border/50 pb-3">
              <div className="p-1.5 bg-primary/10 rounded-lg"><BoxSelect className="h-4 w-4 text-primary" /></div>
              الهندسة والمسافات (Padding)
            </h4>
            
            <div className="grid grid-cols-2 gap-6 pt-4 pb-2 border-b border-white/5">
              {['Top', 'Bottom', 'Right', 'Left'].map((dir) => (
                <div key={dir} className="space-y-2">
                  <div className="flex justify-between">
                    <Label className="text-[10px] uppercase font-bold text-muted-foreground">{dir === 'Top' ? 'أعلى' : dir === 'Bottom' ? 'أسفل' : dir === 'Right' ? 'يمين' : 'يسار'}</Label>
                    <span className="text-[10px] font-mono font-bold text-primary">{props[`padding${dir}`] || 0}</span>
                  </div>
                  <input 
                    type="range" min="0" max="16" step="1"
                    value={props[`padding${dir}`] || 0} 
                    onChange={(e) => handlePropChange(`padding${dir}`, parseInt(e.target.value))}
                    className="w-full h-1.5 bg-background rounded-lg appearance-none cursor-pointer accent-primary shadow-inner"
                  />
                </div>
              ))}
            </div>

            <div className="pt-2 space-y-3">
              <div className="flex justify-between">
                <Label className="text-xs font-bold text-muted-foreground">تدوير الحواف (Radius)</Label>
                <span className="text-xs font-mono font-bold text-primary">{props.rounded !== undefined ? props.rounded : 24}px</span>
              </div>
              <input 
                type="range" min="0" max="100" step="4"
                value={props.rounded !== undefined ? props.rounded : 24} 
                onChange={(e) => handlePropChange('rounded', parseInt(e.target.value))}
                className="w-full h-1.5 bg-background rounded-lg appearance-none cursor-pointer accent-primary shadow-inner"
              />
            </div>
          </div>

          {/* التأثيرات السينمائية */}
          <div className="space-y-5 bg-primary/5 backdrop-blur-md p-5 rounded-2xl border border-primary/20 shadow-[0_0_30px_rgba(var(--primary-rgb),0.1)] relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 blur-[50px] rounded-full pointer-events-none" />
            
            <h4 className="text-sm font-black text-primary mb-2 flex items-center gap-2 border-b border-primary/20 pb-3 relative z-10">
              <Sparkles className="h-4 w-4" /> التأثيرات السينمائية السيادية
            </h4>
            
            <div className="space-y-4 pt-2 relative z-10">
              <div className="flex items-center justify-between bg-background/40 p-3 rounded-xl border border-white/5">
                <Label className="text-xs font-bold cursor-pointer text-foreground">تأثير الزجاج (Glassmorphism)</Label>
                <Switch checked={props.isGlass || false} onCheckedChange={(c) => handlePropChange('isGlass', c)} />
              </div>

              <div className="flex items-center justify-between bg-background/40 p-3 rounded-xl border border-white/5">
                <Label className="text-xs font-bold cursor-pointer text-foreground">توهج نيون (Neon Glow)</Label>
                <Switch checked={props.hasNeon || false} onCheckedChange={(c) => handlePropChange('hasNeon', c)} />
              </div>

              {props.hasNeon && (
                 <div className="flex items-center justify-between bg-background/40 p-3 rounded-xl border border-primary/20 animate-in fade-in zoom-in duration-300">
                   <Label className="text-xs font-bold text-primary">لون النيون</Label>
                   <Input type="color" value={props.neonColor || "#06b6d4"} onChange={(e) => handlePropChange('neonColor', e.target.value)} className="w-10 h-10 p-0 border-0 rounded-lg cursor-pointer ring-2 ring-primary/30 shadow-md" />
                 </div>
              )}
            </div>
          </div>

        </TabsContent>
      </Tabs>
    </div>
  );
}