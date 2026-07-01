// components/health/BioProfileManager.tsx
'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateMyProfile } from '@/services/health';
import { Loader2, Leaf, PawPrint, Droplet, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TargetEntityType, MedicalProfile } from '@/types/health';

interface BioProfileManagerProps {
  profile: MedicalProfile;
}

const entityTypes: { value: TargetEntityType; label: string; icon: React.ReactNode }[] = [
  { value: 'HUMAN', label: 'بشر', icon: <User className="w-4 h-4" /> },
  { value: 'ANIMAL', label: 'حيوان', icon: <PawPrint className="w-4 h-4" /> },
  { value: 'PLANT', label: 'نبات', icon: <Leaf className="w-4 h-4" /> },
  { value: 'ALGAE', label: 'طحالب', icon: <Droplet className="w-4 h-4" /> },
];

export default function BioProfileManager({ profile }: BioProfileManagerProps) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<Partial<MedicalProfile>>({
    target_entity_type: profile.target_entity_type,
    species: profile.species || '',
    breed: profile.breed || '',
    plant_variety: profile.plant_variety || '',
    scientific_name: profile.scientific_name || '',
    blood_type: profile.blood_type || '',
    chronic_diseases: profile.chronic_diseases || [],
    allergies: profile.allergies || [],
    current_medications: profile.current_medications || [],
    emergency_contact: profile.emergency_contact || '',
  });

  const [newDisease, setNewDisease] = useState('');
  const [newAllergy, setNewAllergy] = useState('');
  const [newMedication, setNewMedication] = useState('');

  const mutation = useMutation({
    mutationFn: (data: Partial<MedicalProfile>) => updateMyProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['health-profile'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(formData);
  };

  const addItem = (field: 'chronic_diseases' | 'allergies' | 'current_medications', value: string) => {
    if (!value.trim()) return;
    setFormData((prev) => ({
      ...prev,
      [field]: [...(prev[field] || []), value.trim()],
    }));
    if (field === 'chronic_diseases') setNewDisease('');
    if (field === 'allergies') setNewAllergy('');
    if (field === 'current_medications') setNewMedication('');
  };

  const removeItem = (field: 'chronic_diseases' | 'allergies' | 'current_medications', index: number) => {
    setFormData((prev) => ({
      ...prev,
      [field]: (prev[field] || []).filter((_, i) => i !== index),
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 p-6">
      {/* نوع الكائن */}
      <div>
        <label className="text-sm font-medium text-foreground/80">نوع الكائن الحي</label>
        <div className="grid grid-cols-4 gap-2 mt-1.5">
          {entityTypes.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => setFormData((prev) => ({ ...prev, target_entity_type: type.value }))}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-xl border transition-all duration-200 text-sm",
                formData.target_entity_type === type.value
                  ? "border-primary/50 bg-primary/20 text-primary"
                  : "border-white/10 bg-white/5 text-muted-foreground/70 hover:bg-white/10"
              )}
            >
              {type.icon}
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* حقول خاصة حسب النوع */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {formData.target_entity_type === 'ANIMAL' && (
          <>
            <div>
              <label className="text-sm font-medium text-foreground/80">النوع (Species)</label>
              <input
                type="text"
                value={formData.species || ''}
                onChange={(e) => setFormData((prev) => ({ ...prev, species: e.target.value }))}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="Canis lupus"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground/80">السلالة (Breed)</label>
              <input
                type="text"
                value={formData.breed || ''}
                onChange={(e) => setFormData((prev) => ({ ...prev, breed: e.target.value }))}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="Golden Retriever"
              />
            </div>
          </>
        )}

        {formData.target_entity_type === 'PLANT' && (
          <>
            <div>
              <label className="text-sm font-medium text-foreground/80">الصنف (Variety)</label>
              <input
                type="text"
                value={formData.plant_variety || ''}
                onChange={(e) => setFormData((prev) => ({ ...prev, plant_variety: e.target.value }))}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="نخيل مجدول"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground/80">الاسم العلمي</label>
              <input
                type="text"
                value={formData.scientific_name || ''}
                onChange={(e) => setFormData((prev) => ({ ...prev, scientific_name: e.target.value }))}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="Phoenix dactylifera"
              />
            </div>
          </>
        )}

        {formData.target_entity_type === 'ALGAE' && (
          <div className="md:col-span-2">
            <label className="text-sm font-medium text-foreground/80">الاسم العلمي</label>
            <input
              type="text"
              value={formData.scientific_name || ''}
              onChange={(e) => setFormData((prev) => ({ ...prev, scientific_name: e.target.value }))}
              className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              placeholder="Chlorella vulgaris"
            />
          </div>
        )}

        {formData.target_entity_type === 'HUMAN' && (
          <div>
            <label className="text-sm font-medium text-foreground/80">فصيلة الدم</label>
            <select
              value={formData.blood_type || ''}
              onChange={(e) => setFormData((prev) => ({ ...prev, blood_type: e.target.value }))}
              className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            >
              <option value="">اختر</option>
              <option value="A+">A+</option>
              <option value="A-">A-</option>
              <option value="B+">B+</option>
              <option value="B-">B-</option>
              <option value="AB+">AB+</option>
              <option value="AB-">AB-</option>
              <option value="O+">O+</option>
              <option value="O-">O-</option>
            </select>
          </div>
        )}
      </div>

      {/* الأمراض المزمنة */}
      <div>
        <label className="text-sm font-medium text-foreground/80">الأمراض المزمنة</label>
        <div className="flex gap-2 mt-1.5">
          <input
            type="text"
            value={newDisease}
            onChange={(e) => setNewDisease(e.target.value)}
            placeholder="مرض السكري"
            className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
          <button
            type="button"
            onClick={() => addItem('chronic_diseases', newDisease)}
            className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            إضافة
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {(formData.chronic_diseases || []).map((item, idx) => (
            <span
              key={idx}
              className="flex items-center gap-1 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-sm"
            >
              {item}
              <button
                type="button"
                onClick={() => removeItem('chronic_diseases', idx)}
                className="text-red-500/50 hover:text-red-500"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      </div>

      {/* الحساسية */}
      <div>
        <label className="text-sm font-medium text-foreground/80">الحساسية</label>
        <div className="flex gap-2 mt-1.5">
          <input
            type="text"
            value={newAllergy}
            onChange={(e) => setNewAllergy(e.target.value)}
            placeholder="حساسية الفول السوداني"
            className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
          <button
            type="button"
            onClick={() => addItem('allergies', newAllergy)}
            className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            إضافة
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {(formData.allergies || []).map((item, idx) => (
            <span
              key={idx}
              className="flex items-center gap-1 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-sm"
            >
              {item}
              <button
                type="button"
                onClick={() => removeItem('allergies', idx)}
                className="text-red-500/50 hover:text-red-500"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      </div>

      {/* الأدوية الحالية */}
      <div>
        <label className="text-sm font-medium text-foreground/80">الأدوية الحالية</label>
        <div className="flex gap-2 mt-1.5">
          <input
            type="text"
            value={newMedication}
            onChange={(e) => setNewMedication(e.target.value)}
            placeholder="الباراسيتامول 500mg"
            className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
          <button
            type="button"
            onClick={() => addItem('current_medications', newMedication)}
            className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            إضافة
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {(formData.current_medications || []).map((item, idx) => (
            <span
              key={idx}
              className="flex items-center gap-1 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-sm"
            >
              {item}
              <button
                type="button"
                onClick={() => removeItem('current_medications', idx)}
                className="text-red-500/50 hover:text-red-500"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      </div>

      {/* جهة الاتصال في الطوارئ */}
      <div>
        <label className="text-sm font-medium text-foreground/80">جهة الاتصال في الطوارئ</label>
        <input
          type="text"
          value={formData.emergency_contact || ''}
          onChange={(e) => setFormData((prev) => ({ ...prev, emergency_contact: e.target.value }))}
          className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="الاسم ورقم الهاتف"
        />
      </div>

      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
      >
        {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'حفظ الملف الطبي'}
      </button>
    </form>
  );
}