// app/(dashboard)/arbitration-syndicates/licenses/page.tsx
'use client';

import { useMyLicenses, useIssueLicense } from '@/hooks/arbitration-syndicates/useLicenses';
import { useSyndicates } from '@/hooks/arbitration-syndicates/useSyndicates';
import { Loader2, Shield, Plus } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns/ar';
import { v4 as uuidv4 } from 'uuid';

export default function LicensesPage() {
  const { data: licenses, isLoading: lLoading } = useMyLicenses();
  const { data: syndicates, isLoading: sLoading } = useSyndicates();
  const issueLicense = useIssueLicense();

  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    syndicate_id: 0,
    license_name: '',
    required_certificate_id: undefined as number | undefined,
    qualifies_for_job_id: undefined as number | undefined,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const idempotencyKey = `license-${uuidv4()}`;
    issueLicense.mutate(
      {
        data: formData,
        idempotencyKey,
      },
      {
        onSuccess: () => {
          setShowForm(false);
          setFormData({ syndicate_id: 0, license_name: '', required_certificate_id: undefined, qualifies_for_job_id: undefined });
        },
      }
    );
  };

  if (lLoading || sLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground/90">📜 تراخيصي المهنية</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          ترخيص جديد
        </button>
      </div>

      {showForm && (
        <div className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="text-lg font-semibold text-foreground/90">✏️ إصدار ترخيص جديد</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground/60">النقابة</label>
              <select
                value={formData.syndicate_id}
                onChange={(e) => setFormData({ ...formData, syndicate_id: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                required
              >
                <option value="">اختر نقابة</option>
                {syndicates?.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">اسم الترخيص</label>
              <input
                type="text"
                value={formData.license_name}
                onChange={(e) => setFormData({ ...formData, license_name: e.target.value })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="مثال: مهندس مدني"
                required
              />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleSubmit}
              disabled={issueLicense.isPending || !formData.syndicate_id || !formData.license_name}
              className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {issueLicense.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
              إصدار
            </button>
            <button
              onClick={() => { setShowForm(false); setFormData({ syndicate_id: 0, license_name: '', required_certificate_id: undefined, qualifies_for_job_id: undefined }); }}
              className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}

      {licenses?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Shield className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد تراخيص</p>
          <p className="text-sm">احصل على ترخيصك المهني الأول</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {licenses?.map((license) => (
            <div key={license.id} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-medium text-foreground/80">{license.license_name}</h4>
                  <p className="text-sm text-muted-foreground/60">{license.syndicate_name || `نقابة #${license.syndicate_id}`}</p>
                </div>
                <span className={cn(
                  "text-xs px-2 py-0.5 rounded-full border",
                  license.status === 'VALID' ? "border-emerald-500/30 text-emerald-500" : "border-red-500/30 text-red-500"
                )}>
                  {license.status}
                </span>
              </div>
              <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
                <div className="flex items-center gap-2">
                  <Shield className="w-3 h-3" />
                  {license.license_number}
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="w-3 h-3" />
                  {format(new Date(license.issue_date), 'dd/MM/yyyy')} - {format(new Date(license.expiry_date), 'dd/MM/yyyy')}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}