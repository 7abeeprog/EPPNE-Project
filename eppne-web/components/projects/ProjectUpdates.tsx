// components/projects/ProjectUpdates.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProjectUpdates, addProjectUpdate } from '@/services/projects';
import { formatDistanceToNow } from 'date-fns/ar';
import { Loader2, Plus, X, Image as ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProjectUpdatesProps {
  projectId: number;
}

export default function ProjectUpdates({ projectId }: ProjectUpdatesProps) {
  const queryClient = useQueryClient();
  const [isAdding, setIsAdding] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [mediaUrls, setMediaUrls] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['project-updates', projectId],
    queryFn: () => getProjectUpdates(projectId, { limit: 20 }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const addMutation = useMutation({
    mutationFn: () =>
      addProjectUpdate(projectId, {
        title,
        content,
        media_urls: mediaUrls ? mediaUrls.split(',').map(u => u.trim()).filter(Boolean) : [],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-updates', projectId] });
      setIsAdding(false);
      setTitle('');
      setContent('');
      setMediaUrls('');
    },
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-32">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* زر إضافة تحديث */}
      <button
        onClick={() => setIsAdding(true)}
        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm"
      >
        <Plus className="w-4 h-4" />
        إضافة تحديث
      </button>

      {/* نموذج الإضافة */}
      {isAdding && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-foreground/80">تحديث جديد</h4>
            <button onClick={() => setIsAdding(false)} className="p-1 rounded-lg hover:bg-white/10">
              <X className="w-4 h-4 text-muted-foreground/60" />
            </button>
          </div>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="عنوان التحديث"
            className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={3}
            placeholder="محتوى التحديث..."
            className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
          />
          <div>
            <label className="text-xs text-muted-foreground/60">روابط الميديا (اختياري، مفصولة بفواصل)</label>
            <input
              type="text"
              value={mediaUrls}
              onChange={(e) => setMediaUrls(e.target.value)}
              placeholder="https://example.com/image1.jpg, https://example.com/image2.jpg"
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
          <button
            onClick={() => addMutation.mutate()}
            disabled={addMutation.isPending || !title || !content}
            className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {addMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'نشر التحديث'}
          </button>
        </div>
      )}

      {/* قائمة التحديثات */}
      {data?.length === 0 ? (
        <div className="p-8 text-center text-muted-foreground/60 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <p>لا توجد تحديثات بعد</p>
        </div>
      ) : (
        data?.map((update) => (
          <div
            key={update.id}
            className="p-4 rounded-2xl bg-card/20 backdrop-blur-sm border border-white/5 hover:border-white/10 transition-all"
          >
            <div className="flex items-start justify-between">
              <h4 className="font-medium text-foreground/80">{update.title}</h4>
              <span className="text-xs text-muted-foreground/40">
                {formatDistanceToNow(new Date(update.created_at), { addSuffix: true })}
              </span>
            </div>
            <p className="text-sm text-foreground/70 mt-1 whitespace-pre-wrap">{update.content}</p>
            {update.media_urls.length > 0 && (
              <div className="flex gap-2 mt-2">
                {update.media_urls.map((url, idx) => (
                  <a key={idx} href={url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary/70 hover:text-primary">
                    📎 مرفق {idx + 1}
                  </a>
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}