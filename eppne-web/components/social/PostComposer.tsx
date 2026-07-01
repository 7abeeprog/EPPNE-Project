// components/social/PostComposer.tsx
'use client';

import { useState } from 'react';
import { useCreatePost } from '@/hooks/social/usePosts';
import { useGroups } from '@/hooks/social/useGroups';
import { Image, Video, FileText, Loader2, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PostComposerProps {
  onClose?: () => void;
  className?: string;
  groupId?: number;
  pageId?: number;
}

export default function PostComposer({ onClose, className, groupId, pageId }: PostComposerProps) {
  const [content, setContent] = useState('');
  const [postType, setPostType] = useState<'TEXT' | 'IMAGE' | 'VIDEO' | 'DOCUMENT'>('TEXT');
  const [mediaUrls, setMediaUrls] = useState<string[]>([]);
  const [shareReward, setShareReward] = useState(0);
  const { data: groups } = useGroups();

  const createPost = useCreatePost();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createPost.mutate(
      {
        content: content.trim() || undefined,
        post_type: postType,
        media_urls: mediaUrls,
        group_id: groupId,
        page_id: pageId,
        share_reward_mr7: shareReward,
      },
      {
        onSuccess: () => {
          setContent('');
          setMediaUrls([]);
          setShareReward(0);
          onClose?.();
        },
      }
    );
  };

  return (
    <div className={cn("p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10", className)}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="ماذا تريد أن تشارك؟"
          rows={3}
          className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none text-foreground/80 placeholder:text-muted-foreground/40"
        />

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPostType('TEXT')}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs border transition-all",
              postType === 'TEXT' ? "border-primary/50 bg-primary/20 text-primary" : "border-white/10 text-muted-foreground/60"
            )}
          >
            <FileText className="w-4 h-4 inline mr-1" />
            نص
          </button>
          <button
            type="button"
            onClick={() => setPostType('IMAGE')}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs border transition-all",
              postType === 'IMAGE' ? "border-primary/50 bg-primary/20 text-primary" : "border-white/10 text-muted-foreground/60"
            )}
          >
            <Image className="w-4 h-4 inline mr-1" />
            صورة
          </button>
          <button
            type="button"
            onClick={() => setPostType('VIDEO')}
            className={cn(
              "px-3 py-1.5 rounded-xl text-xs border transition-all",
              postType === 'VIDEO' ? "border-primary/50 bg-primary/20 text-primary" : "border-white/10 text-muted-foreground/60"
            )}
          >
            <Video className="w-4 h-4 inline mr-1" />
            فيديو
          </button>
        </div>

        {postType !== 'TEXT' && (
          <div>
            <input
              type="text"
              value={mediaUrls.join(', ')}
              onChange={(e) => setMediaUrls(e.target.value.split(',').map(u => u.trim()).filter(Boolean))}
              placeholder="رابط الميديا (مفصول بفواصل)"
              className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
        )}

        <div>
          <label className="text-xs text-muted-foreground/50">مكافأة المشاركة (MR7)</label>
          <input
            type="number"
            step="0.01"
            value={shareReward}
            onChange={(e) => setShareReward(parseFloat(e.target.value) || 0)}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            placeholder="0.00"
          />
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={createPost.isPending || !content.trim()}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50"
          >
            {createPost.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            نشر
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
            >
              إلغاء
            </button>
          )}
        </div>
      </form>
    </div>
  );
}