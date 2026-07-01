// components/projects/ContributionModal.tsx
'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { addContribution } from '@/services/projects';
import { X, Loader2, Wallet, Landmark, Clock, Briefcase, Wrench, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import { v4 as uuidv4 } from 'uuid';
import type { ContributionType } from '@/types/projects';

interface ContributionModalProps {
  projectId: number;
}

const contributionTypes: { value: ContributionType; label: string; icon: React.ReactNode }[] = [
  { value: 'MONETARY', label: 'مالي', icon: <Wallet className="w-4 h-4" /> },
  { value: 'LAND', label: 'أرض', icon: <Landmark className="w-4 h-4" /> },
  { value: 'FACILITY', label: 'منشأة', icon: <Building2 className="w-4 h-4" /> },
  { value: 'LABOR_HOURS', label: 'ساعات عمل', icon: <Clock className="w-4 h-4" /> },
  { value: 'EQUIPMENT', label: 'معدات', icon: <Wrench className="w-4 h-4" /> },
  { value: 'CONSULTING', label: 'استشارات', icon: <Briefcase className="w-4 h-4" /> },
];

export default function ContributionModal({ projectId }: ContributionModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [contribType, setContribType] = useState<ContributionType>('MONETARY');
  const [amount, setAmount] = useState('');
  const [landArea, setLandArea] = useState('');
  const [laborHours, setLaborHours] = useState('');
  const [consultingHours, setConsultingHours] = useState('');
  const [equipmentDesc, setEquipmentDesc] = useState('');

  const queryClient = useQueryClient();
  const router = useRouter();

  // توليد Idempotency Key عند فتح النافذة
  const [idempotencyKey] = useState(() => `contribution-${uuidv4()}`);

  const mutation = useMutation({
    mutationFn: () => {
      const payload: any = {
        project_id: projectId,
        contribution_type: contribType,
      };

      if (contribType === 'MONETARY') {
        payload.amount_mrusdt = parseFloat(amount) || 0;
      } else if (contribType === 'LAND') {
        payload.land_area_sqm = parseFloat(landArea) || 0;
      } else if (contribType === 'LABOR_HOURS') {
        payload.labor_hours = parseFloat(laborHours) || 0;
      } else if (contribType === 'CONSULTING') {
        payload.consulting_hours = parseFloat(consultingHours) || 0;
      } else if (contribType === 'EQUIPMENT') {
        payload.equipment_description = equipmentDesc;
        payload.equipment_estimated_value = parseFloat(amount) || 0;
      }

      return addContribution(payload, idempotencyKey);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project-analytics', projectId] });
      setIsOpen(false);
      resetForm();
    },
  });

  const resetForm = () => {
    setAmount('');
    setLandArea('');
    setLaborHours('');
    setConsultingHours('');
    setEquipmentDesc('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 left-1/2 -translate-x-1/2 px-6 py-3 rounded-2xl bg-primary text-primary-foreground font-medium shadow-[0_0_60px_rgba(var(--primary-rgb),0.4)] hover:shadow-[0_0_80px_rgba(var(--primary-rgb),0.6)] transition-all duration-300 z-40"
      >
        💰 ساهم في هذا المشروع
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        {/* شريط علوي */}
        <div className="absolute top-0 left-0 right-0 h-1 rounded-t-3xl bg-gradient-to-r from-primary to-secondary" />

        {/* زر الإغلاق */}
        <button
          onClick={() => { setIsOpen(false); resetForm(); }}
          className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors"
        >
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        {/* الهيدر */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-xl bg-primary/20 text-primary">
            <Wallet className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-foreground/90">المساهمة في المشروع</h3>
            <p className="text-xs text-muted-foreground/50">اختر نوع المساهمة والمبلغ</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* نوع المساهمة */}
          <div>
            <label className="text-sm font-medium text-foreground/80">نوع المساهمة</label>
            <div className="grid grid-cols-3 gap-2 mt-1.5">
              {contributionTypes.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setContribType(type.value)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-2 rounded-xl border transition-all duration-200 text-sm",
                    contribType === type.value
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

          {/* حقول ديناميكية حسب النوع */}
          {contribType === 'MONETARY' && (
            <div>
              <label className="text-sm font-medium text-foreground/80">المبلغ (MR_USDT)</label>
              <input
                type="number"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
                placeholder="1000.00"
                required
              />
            </div>
          )}

          {contribType === 'LAND' && (
            <div>
              <label className="text-sm font-medium text-foreground/80">المساحة (م²)</label>
              <input
                type="number"
                step="0.01"
                value={landArea}
                onChange={(e) => setLandArea(e.target.value)}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="1000"
                required
              />
            </div>
          )}

          {contribType === 'LABOR_HOURS' && (
            <div>
              <label className="text-sm font-medium text-foreground/80">عدد ساعات العمل</label>
              <input
                type="number"
                step="0.5"
                value={laborHours}
                onChange={(e) => setLaborHours(e.target.value)}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="40"
                required
              />
            </div>
          )}

          {contribType === 'CONSULTING' && (
            <div>
              <label className="text-sm font-medium text-foreground/80">عدد ساعات الاستشارات</label>
              <input
                type="number"
                step="0.5"
                value={consultingHours}
                onChange={(e) => setConsultingHours(e.target.value)}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="20"
                required
              />
            </div>
          )}

          {contribType === 'EQUIPMENT' && (
            <div>
              <label className="text-sm font-medium text-foreground/80">وصف المعدات</label>
              <input
                type="text"
                value={equipmentDesc}
                onChange={(e) => setEquipmentDesc(e.target.value)}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="حفارة، جرار، إلخ"
                required
              />
              <div className="mt-2">
                <label className="text-sm font-medium text-foreground/80">القيمة التقديرية (MR_USDT)</label>
                <input
                  type="number"
                  step="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                  placeholder="5000.00"
                  required
                />
              </div>
            </div>
          )}

          {contribType === 'FACILITY' && (
            <div>
              <label className="text-sm font-medium text-foreground/80">وصف المنشأة</label>
              <textarea
                value={equipmentDesc}
                onChange={(e) => setEquipmentDesc(e.target.value)}
                rows={2}
                className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="مستودع، مكتب، ورشة، إلخ"
                required
              />
            </div>
          )}

          {/* أزرار الإجراء */}
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wallet className="w-4 h-4" />}
              {mutation.isPending ? 'جاري الإرسال...' : 'تأكيد المساهمة'}
            </button>
            <button
              type="button"
              onClick={() => { setIsOpen(false); resetForm(); }}
              className="px-4 py-2.5 rounded-xl border border-white/10 hover:bg-white/5 transition-colors text-foreground/70"
            >
              إلغاء
            </button>
          </div>

          {/* ملاحظة Idempotency */}
          <div className="text-[10px] text-muted-foreground/30 text-center">
            🔒 معرف العملية: {idempotencyKey.slice(0, 8)}... (لمنع التكرار)
          </div>
        </form>
      </div>
    </div>
  );
}