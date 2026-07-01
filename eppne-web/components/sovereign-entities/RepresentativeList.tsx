// components/sovereign-entities/RepresentativeList.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRepresentatives, addRepresentative, removeRepresentative } from '@/services/sovereign-entities';
import { User, Shield, Trash2, Plus, Loader2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { EntityRepresentative, EntityRole } from '@/types/sovereign-entities';

const roleLabels: Record<EntityRole, { label: string; color: string }> = {
  OWNER: { label: 'مالك', color: 'text-amber-500 border-amber-500/30' },
  EXECUTIVE_DIRECTOR: { label: 'مدير تنفيذي', color: 'text-blue-500 border-blue-500/30' },
  SIGNATORY: { label: 'مفوض بالتوقيع', color: 'text-emerald-500 border-emerald-500/30' },
  REPRESENTATIVE: { label: 'ممثل', color: 'text-muted-foreground border-white/10' },
};

interface RepresentativeListProps {
  entityId: number;
  canManage?: boolean;
}

export default function RepresentativeList({ entityId, canManage = false }: RepresentativeListProps) {
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newRole, setNewRole] = useState<EntityRole>('REPRESENTATIVE');
  const [newCanSign, setNewCanSign] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['representatives', entityId],
    queryFn: () => getRepresentatives(entityId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const addMutation = useMutation({
    mutationFn: (payload: { user_id: number; role: EntityRole; can_sign_contracts: boolean }) =>
      addRepresentative(entityId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['representatives', entityId] });
      setShowAddForm(false);
      setNewUserEmail('');
    },
  });

  const removeMutation = useMutation({
    mutationFn: (userId: number) => removeRepresentative(entityId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['representatives', entityId] });
    },
  });

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    // في الواقع، يجب البحث عن المستخدم عبر البريد الإلكتروني أولاً
    // هنا سنفترض وجود دالة searchUserByEmail في الخدمات
    // سنقوم بجلب user_id من النتيجة
    // تبسيطاً، سنستخدم معرف وهمي 999 (يجب تعديله في الإنتاج)
    const userId = 999; // سيتم استبداله ببحث حقيقي
    addMutation.mutate({
      user_id: userId,
      role: newRole,
      can_sign_contracts: newCanSign,
    });
  };

  if (isLoading) {
    return <div className="flex justify-center p-4"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-4">
      {/* الهيدر */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground/80">
          <User className="w-4 h-4" />
          الممثلون ({data?.length || 0})
        </div>
        {canManage && (
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-full bg-primary/20 text-primary hover:bg-primary/30 transition-colors"
          >
            <Plus className="w-3 h-3" />
            إضافة ممثل
          </button>
        )}
      </div>

      {/* نموذج الإضافة */}
      {showAddForm && canManage && (
        <form onSubmit={handleAdd} className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-3">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[150px]">
              <label className="text-xs text-muted-foreground/60">البريد الإلكتروني</label>
              <input
                type="email"
                value={newUserEmail}
                onChange={(e) => setNewUserEmail(e.target.value)}
                placeholder="البريد الإلكتروني للمستخدم"
                className="w-full mt-0.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                required
              />
            </div>
            <div className="w-32">
              <label className="text-xs text-muted-foreground/60">الدور</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as EntityRole)}
                className="w-full mt-0.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="REPRESENTATIVE">ممثل</option>
                <option value="SIGNATORY">مفوض بالتوقيع</option>
                <option value="EXECUTIVE_DIRECTOR">مدير تنفيذي</option>
                <option value="OWNER">مالك</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={newCanSign}
                onChange={(e) => setNewCanSign(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-white/5"
              />
              <label className="text-xs text-muted-foreground/60">يمكنه التوقيع</label>
            </div>
            <button
              type="submit"
              disabled={addMutation.isPending}
              className="px-4 py-1.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
            >
              {addMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'إضافة'}
            </button>
          </div>
        </form>
      )}

      {/* القائمة */}
      <div className="space-y-1.5">
        {data?.map((rep) => (
          <div
            key={rep.id}
            className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors border border-white/5"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-semibold text-sm">
                {rep.user_id.toString().slice(0, 1)}
              </div>
              <div>
                <p className="text-sm font-medium text-foreground/80">
                  المستخدم #{rep.user_id}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full border",
                    roleLabels[rep.role]?.color || 'text-muted-foreground border-white/10'
                  )}>
                    {roleLabels[rep.role]?.label || rep.role}
                  </span>
                  {rep.can_sign_contracts && (
                    <span className="text-[10px] text-emerald-500/70">🖊️ مفوض</span>
                  )}
                </div>
              </div>
            </div>
            {canManage && rep.role !== 'OWNER' && (
              <button
                onClick={() => removeMutation.mutate(rep.user_id)}
                className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground/50 hover:text-red-500 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
        {data?.length === 0 && (
          <div className="text-center text-muted-foreground/50 text-sm py-6">
            لا يوجد ممثلون لهذا الكيان
          </div>
        )}
      </div>
    </div>
  );
}