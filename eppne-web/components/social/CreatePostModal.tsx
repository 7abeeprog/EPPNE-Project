// components/social/CreatePostModal.tsx
'use client';

import { useState } from 'react';
import { useCreatePost } from '@/hooks/social/usePosts';
import { X, Loader2, Users } from 'lucide-react';
import type { PostType } from '@/types/social';

interface CreatePostModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CreatePostModal({ isOpen, onClose }: CreatePostModalProps) {
  const [content, setContent] = useState('');
  const [postType, setPostType] = useState<PostType>('TEXT');

  const createPost = useCreatePost();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createPost.mutate(
      { content, post_type: postType, media_urls: [], share_reward_mr7: 0 },
      {
        onSuccess: () => {
          onClose();
          setContent('');
          setPostType('TEXT');
        },
      }
    );
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
          منشور جديد
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">نوع المنشور</label>
            <select
              value={postType}
              onChange={(e) => setPostType(e.target.value as PostType)}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            >
              <option value="TEXT">نص</option>
              <option value="IMAGE">صورة</option>
              <option value="VIDEO">فيديو</option>
              <option value="POLL">استطلاع</option>
              <option value="DOCUMENT">مستند</option>
            </select>
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">المحتوى</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={4}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
              placeholder="بماذا تفكر؟"
              required
            />
          </div>

          <button
            type="submit"
            disabled={createPost.isPending || !content.trim()}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {createPost.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            نشر
          </button>
        </form>
      </div>
    </div>
  );
}
