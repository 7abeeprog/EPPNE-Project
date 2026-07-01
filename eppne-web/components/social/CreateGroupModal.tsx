// components/social/CreateGroupModal.tsx
'use client';

import { useState } from 'react';
import { useCreateGroup } from '@/hooks/social/useGroups';
import { X, Loader2, Users } from 'lucide-react';

interface CreateGroupModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CreateGroupModal({ isOpen, onClose }: CreateGroupModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    privacy: 'PUBLIC' as const,
    linked_project_id: undefined as number | undefined,
  });

  const createGroup = useCreateGroup();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createGroup.mutate(formData, {
      onSuccess: () => {
        onClose();
        setFormData({ name: '', description: '', privacy: 'PUBLIC', linked_project_id: undefined });
      },
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-md p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        <button onClick={onClose} className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors">
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        <h3 className="text-lg font-bold text-foreground/90 flex items-center gap-2">
          <Users className="w-5 h-5 text-primary" />
          إنشاء مجموعة جديدة
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">اسم المجموعة</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              required
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground/60">الوصف</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={2}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground/60">الخصوصية</label>
            <select
              value={formData.privacy}
              onChange={(e) => setFormData({ ...formData, privacy: e.target.value as any })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            >
              <option value="PUBLIC">عامة</option>
              <option value="PRIVATE">خاصة (موافقة مسبقة)</option>
              <option value="SECRET">سرية (غير قابلة للبحث)</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={createGroup.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {createGroup.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            إنشاء المجموعة
          </button>
        </form>
      </div>
    </div>
  );
}