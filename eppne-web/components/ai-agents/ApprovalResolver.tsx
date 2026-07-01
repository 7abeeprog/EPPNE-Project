// components/ai-agents/ApprovalResolver.tsx
'use client';

import { useState } from 'react';
import { X, Loader2, AlertTriangle, Check, Shield, Wallet, FileSignature, Power, Code } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ApprovalRequest } from '@/types/ai-agents';

interface ApprovalResolverProps {
  approval: ApprovalRequest;
  onClose: () => void;
  onResolve: (approvalId: number, status: 'APPROVED' | 'REJECTED', feedback?: string) => void;
  isResolving: boolean;
}

const actionIcons = {
  TRANSFER_FUNDS: { icon: Wallet, label: 'تحويل أموال', color: 'text-amber-500', bg: 'bg-amber-500/10' },
  SIGN_CONTRACT: { icon: FileSignature, label: 'توقيع عقد', color: 'text-blue-500', bg: 'bg-blue-500/10' },
  SHUTDOWN_FACTORY: { icon: Power, label: 'إيقاف تشغيل', color: 'text-red-500', bg: 'bg-red-500/10' },
  DEPLOY_CODE: { icon: Code, label: 'نشر كود', color: 'text-purple-500', bg: 'bg-purple-500/10' },
};

export default function ApprovalResolver({
  approval,
  onClose,
  onResolve,
  isResolving,
}: ApprovalResolverProps) {
  const [feedback, setFeedback] = useState('');
  const [selectedAction, setSelectedAction] = useState<'APPROVED' | 'REJECTED'>('APPROVED');

  const action = actionIcons[approval.action_type] || { 
    icon: Shield, 
    label: approval.action_type, 
    color: 'text-gray-500',
    bg: 'bg-gray-500/10' 
  };
  const Icon = action.icon;

  const isHighRisk = ['TRANSFER_FUNDS', 'SHUTDOWN_FACTORY'].includes(approval.action_type);

  const handleSubmit = () => {
    onResolve(approval.id, selectedAction, feedback.trim() || undefined);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        {/* شريط علوي */}
        <div className={cn(
          "absolute top-0 left-0 right-0 h-1 rounded-t-3xl",
          isHighRisk ? "bg-gradient-to-r from-amber-500 to-red-500" : "bg-gradient-to-r from-primary to-secondary"
        )} />

        {/* زر الإغلاق */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors"
        >
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        {/* الهيدر */}
        <div className="flex items-center gap-3 mb-6">
          <div className={cn("p-2.5 rounded-xl", action.bg, action.color)}>
            <Icon className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-foreground/90">طلب موافقة بشرية</h3>
            <div className="flex items-center gap-2 text-sm text-muted-foreground/60">
              <span>{action.label}</span>
              <span className="text-muted-foreground/30">•</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(approval.created_at).toLocaleString('ar-EG')}
              </span>
            </div>
          </div>
        </div>

        {/* تحذير المخاطر */}
        {isHighRisk && (
          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3 mb-4">
            <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-500/90">⚠️ عملية عالية المخاطر</p>
              <p className="text-xs text-amber-500/70">
                هذا الإجراء يتضمن تحويل أموال أو إيقاف تشغيل. يرجى التأكد من صحة البيانات قبل الموافقة.
              </p>
            </div>
          </div>
        )}

        {/* تفاصيل الطلب */}
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 mb-4">
          <h4 className="text-sm font-medium text-foreground/70 mb-2">📦 بيانات الطلب</h4>
          <div className="space-y-1.5 text-sm font-mono text-foreground/70">
            {Object.entries(approval.proposed_payload).map(([key, value]) => (
              <div key={key} className="flex gap-3 border-b border-white/5 pb-1.5 last:border-0">
                <span className="text-muted-foreground/50 min-w-[100px]">{key}:</span>
                <span className="text-foreground/80 break-all">
                  {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* ملاحظات الحل */}
        <div>
          <label className="text-sm font-medium text-foreground/80">📝 ملاحظاتك (اختياري)</label>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={3}
            placeholder="اكتب سبب قبولك أو رفضك لهذا الطلب..."
            className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80 resize-none"
          />
        </div>

        {/* أزرار الإجراء */}
        <div className="flex gap-3 pt-4 border-t border-white/10 mt-4">
          <button
            onClick={() => setSelectedAction('APPROVED')}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all duration-300",
              selectedAction === 'APPROVED'
                ? "bg-emerald-500 text-white shadow-[0_0_30px_rgba(52,211,153,0.3)]"
                : "bg-white/5 text-muted-foreground/60 hover:bg-white/10"
            )}
          >
            <Check className="w-4 h-4" />
            قبول
          </button>
          <button
            onClick={() => setSelectedAction('REJECTED')}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all duration-300",
              selectedAction === 'REJECTED'
                ? "bg-red-500 text-white shadow-[0_0_30px_rgba(239,68,68,0.3)]"
                : "bg-white/5 text-muted-foreground/60 hover:bg-white/10"
            )}
          >
            <X className="w-4 h-4" />
            رفض
          </button>
          <button
            onClick={handleSubmit}
            disabled={isResolving}
            className="px-6 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {isResolving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'تأكيد القرار'}
          </button>
        </div>

        {/* تعليمات أمنية */}
        <div className="mt-3 text-[10px] text-muted-foreground/30 flex items-center gap-2">
          <Shield className="w-3 h-3" />
          يتم تسجيل جميع القرارات مع وقتها وملاحظاتك لأغراض التدقيق
        </div>
      </div>
    </div>
  );
}