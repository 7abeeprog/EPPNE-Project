// app/(dashboard)/employment/payroll/page.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyPayrolls, generatePayroll, approvePayroll, payPayroll } from '@/services/employment';
import { Loader2, DollarSign, CheckCircle, Shield, Clock, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import StatusBadge from '@/components/employment/StatusBadge';
import ConfirmationModal from '@/components/ui/ConfirmationModal';
import { v4 as uuidv4 } from 'uuid';

export default function PayrollPage() {
  const queryClient = useQueryClient();
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [actionTarget, setActionTarget] = useState<{ id: number; action: 'generate' | 'approve' | 'pay' } | null>(null);
  const [idempotencyKey] = useState(() => `payroll-${uuidv4()}`);

  const { data: payrolls, isLoading } = useQuery({
    queryKey: ['my-payrolls'],
    queryFn: () => getMyPayrolls({ limit: 24 }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const generateMutation = useMutation({
    mutationFn: () => generatePayroll(1, selectedMonth, idempotencyKey),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['my-payrolls'] }),
  });

  const approveMutation = useMutation({
    mutationFn: (payrollId: number) => approvePayroll(payrollId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['my-payrolls'] }),
  });

  const payMutation = useMutation({
    mutationFn: (payrollId: number) => payPayroll(payrollId, idempotencyKey),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['my-payrolls'] }),
  });

  if (isLoading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">💰 كشوف الرواتب</h1>
          <p className="text-sm text-muted-foreground/70">إدارة الرواتب والتسويات المالية</p>
        </div>
        <div className="flex gap-3">
          <input
            type="month"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
          <button
            onClick={() => setActionTarget({ id: 0, action: 'generate' })}
            className="px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
          >
            <DollarSign className="w-4 h-4 inline mr-1" />
            إنشاء كشف
          </button>
        </div>
      </div>

      {payrolls?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <div className="text-4xl mb-4">📊</div>
          <p className="text-lg">لا توجد كشوف رواتب</p>
          <p className="text-sm">سيظهر هنا سجل الرواتب الشهرية</p>
        </div>
      ) : (
        <div className="space-y-4">
          {payrolls?.map((payroll) => (
            <div
              key={payroll.id}
              className="p-5 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all duration-300"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-foreground/90">شهر {payroll.month}</h3>
                    <StatusBadge status={payroll.status} />
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3 text-sm">
                    <div>
                      <span className="text-muted-foreground/50">الراتب الأساسي</span>
                      <p className="font-medium">{payroll.base_salary.toFixed(2)} MR_USDT</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground/50">العمل الإضافي</span>
                      <p className="font-medium text-emerald-500">{payroll.overtime_pay.toFixed(2)} MR_USDT</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground/50">الخصومات</span>
                      <p className="font-medium text-red-500">
                        {Object.values(payroll.deductions).reduce((a, b) => a + b, 0).toFixed(2)} MR_USDT
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground/50">صافي الراتب</span>
                      <p className="font-bold text-primary text-lg">{payroll.net_salary.toFixed(2)} MR_USDT</p>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  {payroll.status === 'DRAFT' && (
                    <button
                      onClick={() => setActionTarget({ id: payroll.id, action: 'approve' })}
                      className="px-3 py-1.5 rounded-xl bg-blue-500/20 text-blue-500 border border-blue-500/30 hover:bg-blue-500/30 transition-colors text-sm"
                    >
                      <CheckCircle className="w-4 h-4 inline mr-1" />
                      اعتماد
                    </button>
                  )}
                  {payroll.status === 'APPROVED' && (
                    <button
                      onClick={() => setActionTarget({ id: payroll.id, action: 'pay' })}
                      className="px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors text-sm"
                    >
                      <DollarSign className="w-4 h-4 inline mr-1" />
                      دفع
                    </button>
                  )}
                  {payroll.status === 'PAID' && (
                    <span className="text-xs text-emerald-500/70 flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" />
                      مدفوع
                    </span>
                  )}
                </div>
              </div>
              {payroll.payment_tx_hash && (
                <div className="mt-3 text-xs text-muted-foreground/40 font-mono">
                  🧾 {payroll.payment_tx_hash}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* تأكيد الإجراءات */}
      <ConfirmationModal
        isOpen={!!actionTarget}
        onClose={() => setActionTarget(null)}
        onConfirm={() => {
          if (!actionTarget) return;
          if (actionTarget.action === 'generate') {
            generateMutation.mutate();
          } else if (actionTarget.action === 'approve') {
            approveMutation.mutate(actionTarget.id);
          } else if (actionTarget.action === 'pay') {
            payMutation.mutate(actionTarget.id);
          }
          setActionTarget(null);
        }}
        title="تأكيد العملية"
        message={
          actionTarget?.action === 'generate'
            ? 'سيتم إنشاء كشف راتب للشهر المحدد'
            : actionTarget?.action === 'approve'
            ? 'سيتم اعتماد كشف الراتب وتصبح جاهزة للدفع'
            : 'سيتم تحويل المبلغ من محفظتك إلى محفظة الموظف'
        }
        confirmText={
          actionTarget?.action === 'generate'
            ? 'إنشاء'
            : actionTarget?.action === 'approve'
            ? 'اعتماد'
            : 'دفع'
        }
        type={
          actionTarget?.action === 'pay' ? 'danger' : 'warning'
        }
        primaryColor="#8CC63F"
        requiresTyping={actionTarget?.action === 'pay'}
        entityName={actionTarget?.action === 'pay' ? 'دفع الراتب' : undefined}
      />
    </div>
  );
}