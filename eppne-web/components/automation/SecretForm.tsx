// components/automation/SecretForm.tsx
'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createSecret } from '@/services/automation.service';
import { X, Loader2, Eye, EyeOff, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SecretFormProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SecretForm({ isOpen, onClose }: SecretFormProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [value, setValue] = useState('');
  const [showValue, setShowValue] = useState(false);

  const createMutation = useMutation({
    mutationFn: createSecret,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['secrets'] });
      setName('');
      setValue('');
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !value.trim()) return;
    createMutation.mutate({ name: name.trim(), value });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-md p-6 rounded-2xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        {/* شريط علوي */}
        <div className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl bg-gradient-to-r from-primary to-secondary" />

        {/* زر الإغلاق */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors"
        >
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        {/* الهيدر */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-xl bg-primary/20 text-primary">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-foreground/90">إضافة سر جديد</h3>
            <p className="text-xs text-muted-foreground/50">سيتم تشفير القيمة قبل تخزينها</p>
          </div>
        </div>

        {/* النموذج */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-foreground/80">اسم السر</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="مثل: STRIPE_API_KEY"
              className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80 transition-colors"
              required
              autoFocus
            />
            <p className="text-[10px] text-muted-foreground/40 mt-1">
              استخدم هذا الاسم في العقد عبر {'{{'}secrets.الاسم{'}}'}
            </p>
          </div>

          <div>
            <label className="text-sm font-medium text-foreground/80">القيمة</label>
            <div className="relative mt-1.5">
              <input
                type={showValue ? 'text' : 'password'}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="••••••••••••••••"
                className="w-full px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80 font-mono transition-colors"
                required
              />
              <button
                type="button"
                onClick={() => setShowValue(!showValue)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-lg hover:bg-white/10 transition-colors text-muted-foreground/50"
              >
                {showValue ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[10px] text-muted-foreground/40 mt-1">
              سيتم تشفير هذه القيمة ولن يمكن قراءتها بعد الحفظ
            </p>
          </div>

          {/* أزرار الإجراء */}
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
              {createMutation.isPending ? 'جاري الحفظ...' : 'حفظ السر'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-white/10 hover:bg-white/5 transition-colors text-foreground/70"
            >
              إلغاء
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}