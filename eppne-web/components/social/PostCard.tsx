// components/social/PostCard.tsx
'use client';

import { useState } from 'react';
import { useLikePost, useSharePost } from '@/hooks/social/usePosts';
import { Heart, Share2, MessageCircle, Sparkles, MoreVertical } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns/ar';
import type { Post } from '@/types/social';
import { v4 as uuidv4 } from 'uuid';

interface PostCardProps {
  post: Post;
  onComment?: (postId: number) => void;
}

export default function PostCard({ post, onComment }: PostCardProps) {
  const [isLiked, setIsLiked] = useState(post.is_liked || false);
  const [likesCount, setLikesCount] = useState(post.likes_count);

  const likeMutation = useLikePost();
  const shareMutation = useSharePost();

  const handleLike = () => {
    const idempotencyKey = `like-${post.id}-${uuidv4()}`;
    likeMutation.mutate(
      { postId: post.id, idempotencyKey },
      {
        onSuccess: (data) => {
          if (data.status === 'success') {
            setIsLiked(true);
            setLikesCount((prev) => prev + 1);
          }
        },
      }
    );
  };

  const handleShare = () => {
    shareMutation.mutate(post.id);
  };

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
          {post.author_name?.[0] || 'U'}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-foreground/80">{post.author_name || `المستخدم #${post.author_id}`}</span>
            {post.green_tag_verified && (
              <span className="text-[10px] text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                موثق
              </span>
            )}
            <span className="text-xs text-muted-foreground/40">
              {formatDistanceToNow(new Date(post.created_at), { addSuffix: true })}
            </span>
          </div>
          {post.content && <p className="mt-1 text-sm text-foreground/70">{post.content}</p>}
          {post.media_urls.length > 0 && (
            <div className="mt-2 grid grid-cols-2 gap-2">
              {post.media_urls.slice(0, 4).map((url, idx) => (
                <div key={idx} className="aspect-square rounded-xl bg-white/5 overflow-hidden">
                  <img src={url} alt={`Media ${idx}`} className="w-full h-full object-cover" />
                </div>
              ))}
            </div>
          )}
          <div className="flex items-center gap-4 mt-3 text-sm">
            <button
              onClick={handleLike}
              disabled={likeMutation.isPending}
              className={cn(
                "flex items-center gap-1 transition-colors",
                isLiked ? "text-red-500" : "text-muted-foreground/50 hover:text-foreground/80"
              )}
            >
              <Heart className={cn("w-4 h-4", isLiked && "fill-red-500")} />
              <span>{likesCount}</span>
            </button>
            <button
              onClick={() => onComment?.(post.id)}
              className="flex items-center gap-1 text-muted-foreground/50 hover:text-foreground/80 transition-colors"
            >
              <MessageCircle className="w-4 h-4" />
              <span>{post.comments_count}</span>
            </button>
            <button
              onClick={handleShare}
              disabled={shareMutation.isPending}
              className="flex items-center gap-1 text-muted-foreground/50 hover:text-foreground/80 transition-colors"
            >
              <Share2 className="w-4 h-4" />
              <span>{post.shares_count}</span>
            </button>
            {post.share_reward_mr7 > 0 && (
              <span className="text-xs text-emerald-500/70">💰 {post.share_reward_mr7} MR7</span>
            )}
          </div>
        </div>
        <button className="p-1 rounded-lg hover:bg-white/10 transition-colors">
          <MoreVertical className="w-4 h-4 text-muted-foreground/50" />
        </button>
      </div>
    </div>
  );
}