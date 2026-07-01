// components/entities/entity-form.tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { SovereignEntityType } from "@/types/entity";
import { Loader2, Building, FileText, Hash, MapPin, Globe, Mail, Phone, Wallet, Palette, ImageIcon, ShieldCheck } from "lucide-react";

const entityTypeLabels: Record<SovereignEntityType, string> = {
  STATE_GOVERNMENT: "دولة / حكومة",
  MINISTRY_AUTHORITY: "وزارة / هيئة حكومية",
  INTERNATIONAL_ORGANIZATION: "منظمة دولية",
  MULTINATIONAL_CORP: "شركة متعددة الجنسيات",
  ENTERPRISE: "شركة / مؤسسة",
  NGO_CIVIL_SOCIETY: "منظمة مجتمع مدني",
  ACADEMIC_INSTITUTION: "جامعة / مركز بحثي",
};

// 🟢 1. إصلاح الـ Schema: التخلص من .nullable() واستخدام .or(z.literal(""))
// لأن حقول React تتعامل مع النصوص الفارغة "" وليس null
const formSchema = z.object({
  name: z.string().min(2, "الاسم قصير جداً").max(255),
  legal_name: z.string().optional().or(z.literal("")),
  entity_type: z.nativeEnum(SovereignEntityType),
  registration_number: z.string().optional().or(z.literal("")),
  tax_id: z.string().optional().or(z.literal("")),
  country_of_origin: z.string().min(2, "الدولة مطلوبة"),
  city: z.string().optional().or(z.literal("")),
  address: z.string().optional().or(z.literal("")),
  official_email: z.string().email("بريد إلكتروني غير صالح"),
  official_phone: z.string().optional().or(z.literal("")),
  website: z.string().url("رابط غير صالح").optional().or(z.literal("")),
  wallet_address: z.string().regex(/^0x[a-fA-F0-9]{40}$/, "عنوان محفظة غير صالح").optional().or(z.literal("")),
  logo_url: z.string().url("رابط الشعار غير صالح").optional().or(z.literal("")),
  cover_image_url: z.string().url("رابط الغلاف غير صالح").optional().or(z.literal("")),
  primary_color: z.string().regex(/^#([A-Fa-f0-9]{6})$/, "لون غير صالح").default("#8CC63F"),
  secondary_color: z.string().regex(/^#([A-Fa-f0-9]{6})$/, "لون غير صالح").default("#06b6d4"),
});

export type EntityFormValues = z.infer<typeof formSchema>;

interface EntityFormProps {
  defaultValues?: any; // 🟢 2. قبول أي نوع لمنع تعارض الـ Null القادم من الباك إند
  onSubmit: (data: EntityFormValues) => Promise<void> | void;
  isLoading?: boolean;
  submitLabel?: string;
}

export function EntityForm({
  defaultValues,
  onSubmit,
  isLoading = false,
  submitLabel = "تأسيس الكيان",
}: EntityFormProps) {
  
  // 🟢 3. تنظيف البيانات القادمة من الباك إند (تحويل null إلى "") لمنع انهيار TypeScript
  const safeDefaultValues: EntityFormValues = {
    name: defaultValues?.name || "",
    legal_name: defaultValues?.legal_name || "",
    registration_number: defaultValues?.registration_number || "",
    tax_id: defaultValues?.tax_id || "",
    country_of_origin: defaultValues?.country_of_origin || "",
    city: defaultValues?.city || "",
    address: defaultValues?.address || "",
    official_email: defaultValues?.official_email || "",
    official_phone: defaultValues?.official_phone || "",
    website: defaultValues?.website || "",
    wallet_address: defaultValues?.wallet_address || "",
    logo_url: defaultValues?.logo_url || "",
    cover_image_url: defaultValues?.cover_image_url || "",
    entity_type: defaultValues?.entity_type || SovereignEntityType.ENTERPRISE,
    primary_color: defaultValues?.primary_color || "#8CC63F",
    secondary_color: defaultValues?.secondary_color || "#06b6d4",
  };

  const form = useForm<EntityFormValues>({
    resolver: zodResolver(formSchema) as any, // 🟢 4. درع حماية ضد تعارض استنتاج الأنواع (Type Inference)
    defaultValues: safeDefaultValues,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        
        {/* القسم الأول: البيانات الأساسية والقانونية */}
        <div className="bg-card/20 backdrop-blur-md border border-white/5 rounded-[2rem] p-6 md:p-8 shadow-inner space-y-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 blur-[50px] rounded-full pointer-events-none" />
          
          <h3 className="text-lg font-black text-foreground flex items-center gap-2 border-b border-white/5 pb-4">
            <Building className="h-5 w-5 text-primary" /> المعلومات الأساسية والقانونية
          </h3>

          <div className="grid gap-6 md:grid-cols-2 relative z-10">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><Building className="h-3.5 w-3.5 text-primary/70"/> اسم الكيان *</FormLabel>
                  <FormControl>
                    <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11" placeholder="مثال: شركة النور للتكنولوجيا" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="legal_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><FileText className="h-3.5 w-3.5 text-primary/70"/> الاسم القانوني</FormLabel>
                  <FormControl>
                    <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11" placeholder="مثال: شركة النور للتكنولوجيا ش.م.م" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="entity_type"
            render={({ field }) => (
              <FormItem className="relative z-10">
                <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><ShieldCheck className="h-3.5 w-3.5 text-primary/70"/> نوع الكيان السيادي *</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger className="bg-background/50 border-white/10 focus:ring-primary rounded-xl h-11 font-bold">
                      <SelectValue placeholder="اختر نوع الكيان" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent className="rounded-xl border-white/10 backdrop-blur-2xl bg-card/90">
                    {Object.entries(entityTypeLabels).map(([value, label]) => (
                      <SelectItem key={value} value={value} className="font-medium">{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="grid gap-6 md:grid-cols-2 relative z-10">
            <FormField
              control={form.control}
              name="registration_number"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><Hash className="h-3.5 w-3.5 text-primary/70"/> رقم التسجيل التجاري</FormLabel>
                  <FormControl>
                    <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11 font-mono" placeholder="123456" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="tax_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><FileText className="h-3.5 w-3.5 text-primary/70"/> الرقم الضريبي</FormLabel>
                  <FormControl>
                    <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11 font-mono" placeholder="123-456-789" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>

        {/* القسم الثاني: الموقع وبيانات الاتصال */}
        <div className="bg-card/20 backdrop-blur-md border border-white/5 rounded-[2rem] p-6 md:p-8 shadow-inner space-y-6 relative overflow-hidden">
          <h3 className="text-lg font-black text-foreground flex items-center gap-2 border-b border-white/5 pb-4 relative z-10">
            <Globe className="h-5 w-5 text-primary" /> الموقع وبيانات الاتصال
          </h3>

          <div className="grid gap-6 md:grid-cols-2 relative z-10">
            <FormField
              control={form.control}
              name="country_of_origin"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><Globe className="h-3.5 w-3.5 text-primary/70"/> الدولة *</FormLabel>
                  <FormControl>
                    <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11" placeholder="مثال: مصر" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="city"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><MapPin className="h-3.5 w-3.5 text-primary/70"/> المدينة</FormLabel>
                  <FormControl>
                    <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11" placeholder="مثال: القاهرة" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="address"
            render={({ field }) => (
              <FormItem className="relative z-10">
                <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><MapPin className="h-3.5 w-3.5 text-primary/70"/> العنوان التفصيلي</FormLabel>
                <FormControl>
                  <Textarea className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl resize-none min-h-[100px]" placeholder="أدخل العنوان الكامل..." {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="grid gap-6 md:grid-cols-2 relative z-10">
            <FormField
              control={form.control}
              name="official_email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><Mail className="h-3.5 w-3.5 text-primary/70"/> البريد الرسمي *</FormLabel>
                  <FormControl>
                    <Input type="email" className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11" placeholder="info@entity.com" dir="ltr" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="official_phone"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><Phone className="h-3.5 w-3.5 text-primary/70"/> الهاتف الرسمي</FormLabel>
                  <FormControl>
                    <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11" placeholder="+20 123 456 789" dir="ltr" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="website"
            render={({ field }) => (
              <FormItem className="relative z-10">
                <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><Globe className="h-3.5 w-3.5 text-primary/70"/> الموقع الإلكتروني</FormLabel>
                <FormControl>
                  <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11" placeholder="https://..." dir="ltr" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* القسم الثالث: الهوية البصرية والخزينة اللامركزية */}
        <div className="bg-card/20 backdrop-blur-md border border-white/5 rounded-[2rem] p-6 md:p-8 shadow-inner space-y-6 relative overflow-hidden">
          <h3 className="text-lg font-black text-foreground flex items-center gap-2 border-b border-white/5 pb-4 relative z-10">
            <Palette className="h-5 w-5 text-primary" /> الهوية والمحفظة السيادية
          </h3>

          <FormField
            control={form.control}
            name="wallet_address"
            render={({ field }) => (
              <FormItem className="relative z-10 bg-emerald-500/5 p-4 rounded-2xl border border-emerald-500/10">
                <FormLabel className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold"><Wallet className="h-4 w-4"/> عنوان الخزينة (Web3 Wallet)</FormLabel>
                <FormControl>
                  <Input className="bg-background border-emerald-500/20 focus-visible:ring-emerald-500 rounded-xl h-11 font-mono text-emerald-700 dark:text-emerald-300" placeholder="0x..." dir="ltr" {...field} />
                </FormControl>
                <FormDescription className="text-emerald-600/70 dark:text-emerald-400/70 text-xs">عنوان محفظة الكيان على البلوكتشين لاستقبال الأرصدة (اختياري)</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="grid gap-6 md:grid-cols-2 relative z-10">
            <FormField
              control={form.control}
              name="primary_color"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-muted-foreground font-bold text-xs uppercase tracking-wider">اللون الأساسي</FormLabel>
                  <div className="flex gap-3 items-center bg-background/50 border border-white/10 rounded-xl p-2">
                    <FormControl>
                      <Input type="color" className="w-10 h-10 p-0 border-0 rounded-lg cursor-pointer shadow-sm" {...field} />
                    </FormControl>
                    <Input value={field.value} onChange={field.onChange} className="flex-1 bg-transparent border-0 focus-visible:ring-0 font-mono font-bold" dir="ltr" />
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="secondary_color"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-muted-foreground font-bold text-xs uppercase tracking-wider">اللون الثانوي</FormLabel>
                  <div className="flex gap-3 items-center bg-background/50 border border-white/10 rounded-xl p-2">
                    <FormControl>
                      <Input type="color" className="w-10 h-10 p-0 border-0 rounded-lg cursor-pointer shadow-sm" {...field} />
                    </FormControl>
                    <Input value={field.value} onChange={field.onChange} className="flex-1 bg-transparent border-0 focus-visible:ring-0 font-mono font-bold" dir="ltr" />
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <div className="grid gap-6 md:grid-cols-2 relative z-10">
            <FormField
              control={form.control}
              name="logo_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><ImageIcon className="h-3.5 w-3.5 text-primary/70"/> رابط الشعار</FormLabel>
                  <FormControl>
                    <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11" placeholder="https://..." dir="ltr" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="cover_image_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2 text-muted-foreground font-bold"><ImageIcon className="h-3.5 w-3.5 text-primary/70"/> صورة الغلاف</FormLabel>
                  <FormControl>
                    <Input className="bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl h-11" placeholder="https://..." dir="ltr" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>

        <Button 
          type="submit" 
          disabled={isLoading} 
          className="w-full h-14 text-lg font-black rounded-2xl shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:scale-[1.02] transition-all"
        >
          {isLoading ? (
            <span className="flex items-center gap-2"><Loader2 className="h-6 w-6 animate-spin" /> جاري التشفير والإرسال...</span>
          ) : (
            submitLabel
          )}
        </Button>
      </form>
    </Form>
  );
}