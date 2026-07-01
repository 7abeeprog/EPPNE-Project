// components/realestate/SmartContractDashboard.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deploySmartContract } from '@/services/realestate';
import { Loader2, Shield, CheckCircle, XCircle, Clock, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ContractType } from '@/types/realestate';

export default function SmartContractDashboard() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [contractType, setContractType] = useState<ContractType>('SALE');
  const [referenceId, setReferenceId] = useState('');
  const [metadata, setMetadata] = useState('{}');

  const mutation = useMutation({
    mutationFn: () => {
      try {
        const parsedMetadata = JSON.parse(metadata);
        return deploySmartContract({
          contract_type: contractType,
          reference_id: parseInt(referenceId),
          contract_metadata: parsedMetadata,
        });
      } catch {
        throw new Error('JSON غير صالح');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['smart-contracts'] });
      setShowForm(false);
      setReferenceId('');
      setMetadata('{}');
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-primary/60" />
          <h3 className="text-lg font-semibold text-foreground/90">محرك العقود الذكية</h3>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          نشر عقد جديد
        </button>
      </div>

      {showForm && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs text-muted-foreground/60">نوع العقد</label>
              <select
                value={contractType}
                onChange={(e) => setContractType(e.target.value as ContractType)}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="SALE">بيع</option>
                <option value="RENTAL">إيجار</option>
                <option value="MORTGAGE">رهن</option>
                <option value="LEASE">إيجار طويل</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground/60">معرف المرجع</label>
              <input
                type="number"
                value={referenceId}
                onChange={(e) => setReferenceId(e.target.value)}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="ID"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground/60">البيانات الوصفية (JSON)</label>
              <input
                type="text"
                value={metadata}
                onChange={(e) => setMetadata(e.target.value)}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono"
                placeholder='{"key": "value"}'
              />
            </div>
          </div>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !referenceId}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            نشر العقد الذكي
          </button>
        </div>
      )}
    </div>
  );
}