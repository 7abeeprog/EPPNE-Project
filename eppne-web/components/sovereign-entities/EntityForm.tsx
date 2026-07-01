// components/sovereign-entities/EntityForm.tsx
'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createEntity } from '@/services/sovereign-entities';
import { Upload, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { EntityFormData, SovereignEntityType } from '@/types/sovereign-entities';

const entityTypeOptions: { value: SovereignEntityType; label: string }[] = [
  { value: 'STATE_GOVERNMENT', label: 'دولة/حكومة' },
  { value: 'MINISTRY_AUTHORITY', label: 'وزارة/هيئة حكومية' },
  { value: 'INTERNATIONAL_ORGANIZATION', label: 'منظمة دولية' },
  { value: 'MULTINATIONAL_CORP', label: 'شركة متعددة الجنسيات' },
  { value: 'ENTERPRISE', label: 'شركة تجارية/صناعية' },
  { value: 'NGO_CIVIL_SOCIETY', label: 'منظمة مجتمع مدني' },
  { value: 'ACADEMIC_INSTITUTION', label: 'مؤسسة أكاديمية' },
];

export default function EntityForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [formData, setFormData] = useState<Partial<EntityFormData>>({
    name: '',
    entity_type: 'ENTERPRISE',
    country_of_origin: '',
    official_email: '',
    primary_color: '#8CC63F',
    secondary_color: '#06b6d4',
  });

  const { mutate, isPending } = useMutation({
    mutationFn: async (data: FormData) => {
      const response = await createEntity(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entities', 'me'] });
      router.push('/sovereign-entities');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data = new FormData();
    
    // إضافة جميع الحقول النصية
    Object.entries(formData).forEach(([key, value]) => {
      if (value !== undefined && value !== null && key !== 'logo_file' && key !== 'cover_image_file') {
        data.append(key, String(value));
      }
    });

    // إضافة الملفات
    if (logoFile) {
      data.append('logo_file', logoFile);
    }

    mutate(data);
  };

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setLogoFile(file);
      const reader = new FileReader();
      reader.onload = (event) => setLogoPreview(event.target?.result as string);
      reader.readAsDataURL(file);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 p-6">
      {/* حقل رفع الشعار */}
      <div className="flex items-center gap-6">
        <div 
          className="relative w-24 h-24 rounded-2xl border-2 border-dashed border-white/20 flex items-center justify-center cursor-pointer hover:border-primary/50 transition-all overflow-hidden bg-white/5"
          onClick={() => fileInputRef.current?.click()}
        >
          {logoPreview ? (
            <img src={logoPreview} alt="Logo" className="w-full h-full object-cover" />
          ) : (
            <Upload className="w-8 h-8 text-muted-foreground/40" />
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleLogoChange}
            className="hidden"
          />
          {logoPreview && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setLogoFile(null); setLogoPreview(null); }}
              className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center text-xs"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
        <div className="text-sm text-muted-foreground/60">
          <p>شعار الكيان</p>
          <p className="text-xs">PNG, JPG, SVG (الحد الأقصى 2MB)</p>
        </div>
      </div>

      {/* الحقول الأساسية */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium text-foreground/80">اسم الكيان *</label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-foreground/80">الاسم القانوني</label>
          <input
            type="text"
            value={formData.legal_name || ''}
            onChange={(e) => setFormData({ ...formData, legal_name: e.target.value })}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-foreground/80">نوع الكيان *</label>
          <select
            required
            value={formData.entity_type}
            onChange={(e) => setFormData({ ...formData, entity_type: e.target.value as SovereignEntityType })}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          >
            {entityTypeOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium text-foreground/80">الدولة *</label>
          <input
            type="text"
            required
            value={formData.country_of_origin}
            onChange={(e) => setFormData({ ...formData, country_of_origin: e.target.value })}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-foreground/80">البريد الإلكتروني الرسمي *</label>
          <input
            type="email"
            required
            value={formData.official_email}
            onChange={(e) => setFormData({ ...formData, official_email: e.target.value })}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-foreground/80">رقم التسجيل</label>
          <input
            type="text"
            value={formData.registration_number || ''}
            onChange={(e) => setFormData({ ...formData, registration_number: e.target.value })}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
        </div>
      </div>

      {/* الألوان */}
      <div className="flex gap-6 items-center">
        <div>
          <label className="text-sm font-medium text-foreground/80">اللون الأساسي</label>
          <input
            type="color"
            value={formData.primary_color}
            onChange={(e) => setFormData({ ...formData, primary_color: e.target.value })}
            className="w-12 h-12 rounded-xl cursor-pointer bg-transparent border border-white/10"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-foreground/80">اللون الثانوي</label>
          <input
            type="color"
            value={formData.secondary_color}
            onChange={(e) => setFormData({ ...formData, secondary_color: e.target.value })}
            className="w-12 h-12 rounded-xl cursor-pointer bg-transparent border border-white/10"
          />
        </div>
      </div>

      {/* أزرار الإجراء */}
      <div className="flex gap-4 pt-4 border-t border-white/10">
        <button
          type="submit"
          disabled={isPending}
          className={cn(
            "flex items-center gap-2 px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium",
            "shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)]",
            "transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          {isPending ? 'جاري الإنشاء...' : 'إنشاء الكيان'}
        </button>
        <button
          type="button"
          onClick={() => router.back()}
          className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors text-foreground/70"
        >
          إلغاء
        </button>
      </div>
    </form>
  );
}