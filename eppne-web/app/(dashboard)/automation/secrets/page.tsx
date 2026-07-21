// app/(dashboard)/automation/secrets/page.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSecrets, deleteSecret } from '@/services/automation.service';
import SecretForm from '@/components/automation/SecretForm';
import { Plus, Trash2, Loader2, Shield, Key, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns/ar';

export default function SecretsPage() {
  const queryClient = useQueryClient();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['secrets'],
    queryFn: () => getSecrets().then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSecret,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['secrets'] });
      setDeleteTarget(null);
    },
  });

  const handleDelete = (name: string) => {
    if (confirm(`هل أنت متأكد من حذف السر "${name}"؟ لا يمكن استعادته.`)) {
      deleteMutation.mutate(name);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* الهيدر */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
            <Key className="w-6 h-6 text-primary" />
            الأسرار (Secrets)
          </h1>
          <p className="text-sm text-muted-foreground/70">تخزين آمن لمفاتيح API والمتغيرات الحساسة</p>
        </div>
        <button
          onClick={() => setIsFormOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          سر جديد
        </button>
      </div>

      {/* القائمة */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : data?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Shield className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد أسرار</p>
          <p className="text-sm">أضف سراً لاستخدامه في إعدادات العقد</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.map((secret) => (
            <div
              key={secret.id}
              className={cn(
                "group relative p-5 rounded-2xl bg-card/30 backdrop-blur-xl border transition-all duration-300",
                "border-white/10 hover:border-primary/30 hover:shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.15)]"
              )}
            >
              {/* شريط علوي */}
              <div className="absolute top-0 left-0 right-0 h-0.5 rounded-t-2xl bg-gradient-to-r from-primary/50 to-transparent" />

              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-primary/60" />
                    <h3 className="font-mono text-sm font-medium text-foreground/90 truncate">
                      {secret.name}
                    </h3>
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground/50">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDistanceToNow(new Date(secret.created_at), { addSuffix: true })}
                    </span>
                    <span className="flex items-center gap-1">
                      <Key className="w-3 h-3" />
                      مشفر
                    </span>
                  </div>
                </div>

                {/* زر الحذف */}
                <button
                  onClick={() => handleDelete(secret.name)}
                  disabled={deleteMutation.isPending && deleteTarget === secret.name}
                  className="p-2 rounded-xl opacity-0 group-hover:opacity-100 hover:bg-red-500/10 transition-all duration-200 text-muted-foreground/50 hover:text-red-500"
                  title="حذف السر"
                >
                  {deleteMutation.isPending && deleteTarget === secret.name ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>

              {/* تلميح الاستخدام */}
              <div className="mt-3 pt-3 border-t border-white/5">
                <code className="text-[10px] text-primary/60 bg-primary/5 px-2 py-1 rounded-lg font-mono">
                  {'{{'}secrets.{secret.name}{'}}'}
                </code>
                <span className="text-[10px] text-muted-foreground/40 mr-2">استخدم في العقد</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* نموذج الإضافة (مودال) */}
      <SecretForm isOpen={isFormOpen} onClose={() => setIsFormOpen(false)} />
    </div>
  );
}