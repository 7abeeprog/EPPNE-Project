// components/ai-agents/AgentForm.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createAgent } from '@/services/ai-agents';
import { 
  Loader2, 
  Shield, 
  AlertTriangle, 
  ChevronDown, 
  ChevronUp,
  Wallet,
  FileText,
  Brain,
  Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { AGENT_ROLE_LABELS, type AgentRole, type AgentFormData } from '@/types/ai-agents';

const BASE_MODELS = ['gemini-1.5-pro', 'gemini-1.5-flash', 'claude-3-opus', 'claude-3-sonnet', 'gpt-4-turbo'];

export default function AgentForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<'basic' | 'advanced'>('basic');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [formData, setFormData] = useState<AgentFormData>({
    name: '',
    role: 'SUPPORT',
    system_prompt: 'You are a helpful AI assistant for EPPNE platform.',
    base_model: 'gemini-1.5-pro',
    can_execute_payments: false,
    can_sign_contracts: false,
    requires_human_approval: true,
    interaction_cost_mrusdt: 0,
  });

  const mutation = useMutation({
    mutationFn: () => createAgent(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      router.push('/ai-agents');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  const handleChange = (key: keyof AgentFormData, value: any) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const isDangerous = formData.can_execute_payments || formData.can_sign_contracts;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* حقل الاسم */}
      <div>
        <label className="text-sm font-medium text-foreground/80">اسم الوكيل *</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          placeholder="أدخل اسماً للوكيل"
          className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80 transition-colors"
          required
        />
      </div>

      {/* اختيار الدور */}
      <div>
        <label className="text-sm font-medium text-foreground/80">الدور *</label>
        <select
          value={formData.role}
          onChange={(e) => handleChange('role', e.target.value as AgentRole)}
          className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
        >
          {Object.entries(AGENT_ROLE_LABELS).map(([key, value]) => (
            <option key={key} value={key}>
              {value.icon} {value.label} – {value.description}
            </option>
          ))}
        </select>
      </div>

      {/* الـ System Prompt */}
      <div>
        <label className="text-sm font-medium text-foreground/80">التعليمات الأساسية (System Prompt) *</label>
        <textarea
          value={formData.system_prompt}
          onChange={(e) => handleChange('system_prompt', e.target.value)}
          rows={4}
          className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70 resize-none"
          placeholder="أدخل التعليمات الأساسية للوكيل..."
          required
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          هذه التعليمات ستحدد شخصية الوكيل وسلوكه الأساسي
        </p>
      </div>

      {/* النموذج الأساسي */}
      <div>
        <label className="text-sm font-medium text-foreground/80">النموذج الأساسي</label>
        <select
          value={formData.base_model}
          onChange={(e) => handleChange('base_model', e.target.value)}
          className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
        >
          {BASE_MODELS.map((model) => (
            <option key={model} value={model}>{model}</option>
          ))}
        </select>
      </div>

      {/* تبويب الإعدادات المتقدمة (الصلاحيات) */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex items-center gap-2 text-sm text-muted-foreground/60 hover:text-foreground/80 transition-colors"
      >
        {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        {showAdvanced ? 'إخفاء الإعدادات المتقدمة' : 'عرض الإعدادات المتقدمة (الصلاحيات)'}
      </button>

      {showAdvanced && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-sm border border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Wallet className="w-4 h-4 text-amber-500/70" />
              <span className="text-sm text-foreground/80">تنفيذ المدفوعات</span>
            </div>
            <div className="relative">
              <input
                type="checkbox"
                checked={formData.can_execute_payments}
                onChange={(e) => handleChange('can_execute_payments', e.target.checked)}
                className="w-5 h-5 rounded border-white/20 bg-white/5 accent-primary"
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-500/70" />
              <span className="text-sm text-foreground/80">التوقيع على العقود</span>
            </div>
            <input
              type="checkbox"
              checked={formData.can_sign_contracts}
              onChange={(e) => handleChange('can_sign_contracts', e.target.checked)}
              className="w-5 h-5 rounded border-white/20 bg-white/5 accent-primary"
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-purple-500/70" />
              <span className="text-sm text-foreground/80">يتطلب موافقة بشرية</span>
            </div>
            <input
              type="checkbox"
              checked={formData.requires_human_approval}
              onChange={(e) => handleChange('requires_human_approval', e.target.checked)}
              className="w-5 h-5 rounded border-white/20 bg-white/5 accent-primary"
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground/60">تكلفة التفاعل (MR_USDT)</label>
            <input
              type="number"
              step="0.0001"
              value={formData.interaction_cost_mrusdt}
              onChange={(e) => handleChange('interaction_cost_mrusdt', parseFloat(e.target.value) || 0)}
              className="w-full mt-1.5 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
              min="0"
              placeholder="0.0000"
            />
          </div>

          {/* تحذير أمني عند تفعيل صلاحيات حساسة */}
          {isDangerous && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <div className="text-xs text-red-400/80">
                <p className="font-medium">⚠️ تحذير أمني</p>
                <p>تمنح هذا الوكيل صلاحيات حساسة (دفع/توقيع). تأكد من استخدامه بحذر وتحت إشراف بشري.</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* أزرار الإجراء */}
      <div className="flex gap-3 pt-4 border-t border-white/10">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
          {mutation.isPending ? 'جاري الإنشاء...' : 'إنشاء الوكيل'}
        </button>
        <button
          type="button"
          onClick={() => router.push('/ai-agents')}
          className="px-4 py-2.5 rounded-xl border border-white/10 hover:bg-white/5 transition-colors text-foreground/70"
        >
          إلغاء
        </button>
      </div>
    </form>
  );
}