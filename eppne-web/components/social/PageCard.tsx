// components/social/PageCard.tsx
'use client';

import { Building2, Users, Check, Plus, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useFollowPage, useUnfollowPage } from '@/hooks/social/usePages';
import type { SocialPage } from '@/types/social';

interface PageCardProps {
  page: SocialPage;
}

export default function PageCard({ page }: PageCardProps) {
  const follow = useFollowPage();
  const unfollow = useUnfollowPage();

  const isFollowing = false; // سيتم جلبها من الـ store أو الـ query

  const handleToggle = () => {
    if (isFollowing) {
      unfollow.mutate(page.id);
    } else {
      follow.mutate(page.id);
    }
  };

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-foreground/80">{page.name}</h4>
            {page.is_verified && (
              <span className="text-[10px] text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Shield className="w-3 h-3" />
                موثقة
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground/60">{page.about}</p>
          <p className="text-xs text-muted-foreground/40">@{page.slug}</p>
          <p className="text-xs text-muted-foreground/30 mt-1 flex items-center gap-1">
            <Users className="w-3 h-3" />
            {page.follower_count || 0} متابع
          </p>
        </div>
        <button
          onClick={handleToggle}
          className={cn(
            "px-3 py-1.5 rounded-xl text-sm font-medium transition-colors",
            isFollowing
              ? "bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30"
              : "bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30"
          )}
        >
          {isFollowing ? 'متابع' : 'متابعة'}
        </button>
      </div>
    </div>
  );
}