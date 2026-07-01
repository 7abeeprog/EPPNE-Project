// app/(dashboard)/insurance/employee-profile/page.tsx
'use client';

import { useMyEmployeeProfile, useCreateEmployeeProfile, useUpdateEmployeeProfile } from '@/hooks/insurance/useEmployeeProfile';
import { Loader2, User, Shield } from 'lucide-react';
import { useState } from 'react';

export default function EmployeeProfilePage() {
  const { data: profile, isLoading } = useMyEmployeeProfile();
  const createProfile = useCreateEmployeeProfile();
  const updateProfile = useUpdateEmployeeProfile();

  const [formData, setFormData] = useState({
    government_insurance_number: '',
    employee_share_percentage: 10,
    employer_share_percentage: 90,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (profile) {
      updateProfile.mutate({ data: formData });
    } else {
      createProfile.mutate({
        user_id: 0, // سيتم تعيينه من الباك إند
        ...formData,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
        <User className="w-6 h-6 text-primary" />
        ملف التأمين للموظف
      </h1>

      <form onSubmit={handleSubmit} className="p-6 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 max-w-lg">
        <div>
          <label className="text-sm text-muted-foreground/60">رقم التأمين الحكومي</label>
          <input
            type="text"
            value={formData.government_insurance_number}
            onChange={(e) => setFormData({ ...formData, government_insurance_number: e.target.value })}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            placeholder="مثال: INS-12345"
            required
          />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-muted-foreground/60">نسبة الموظف (%)</label>
            <input
              type="number"
              min="0"
              max="100"
              value={formData.employee_share_percentage}
              onChange={(e) => setFormData({ ...formData, employee_share_percentage: parseFloat(e.target.value) || 0 })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground/60">نسبة صاحب العمل (%)</label>
            <input
              type="number"
              min="0"
              max="100"
              value={formData.employer_share_percentage}
              onChange={(e) => setFormData({ ...formData, employer_share_percentage: parseFloat(e.target.value) || 0 })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={createProfile.isPending || updateProfile.isPending}
          className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
        >
          {createProfile.isPending || updateProfile.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
          {profile ? 'تحديث الملف' : 'إنشاء الملف'}
        </button>

        {profile && (
          <div className="mt-4 p-3 rounded-xl bg-white/5 border border-white/10 text-sm text-muted-foreground/60">
            <p>إجمالي المساهمات: {profile.total_contributed_mrusdt} MR_USDT</p>
            <p>الحالة: {profile.status}</p>
          </div>
        )}
      </form>
    </div>
  );
}