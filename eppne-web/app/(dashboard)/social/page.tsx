// app/(dashboard)/social/page.tsx
'use client';

import { useState } from 'react';
import { useFeed } from '@/hooks/social/usePosts';
import { useUpcomingOccasions } from '@/hooks/social/useOccasions';
import { useDigitalGifts } from '@/hooks/social/useGifts';
import PostCard from '@/components/social/PostCard';
import CreatePostModal from '@/components/social/CreatePostModal';
import CreateOccasionModal from '@/components/social/CreateOccasionModal';
import { Loader2, Plus, Bell, Gift, Calendar, Users } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function SocialDashboard() {
  const [createPostOpen, setCreatePostOpen] = useState(false);
  const [createOccasionOpen, setCreateOccasionOpen] = useState(false);

  const { data: posts, isLoading } = useFeed({ limit: 20 });
  const { data: occasions } = useUpcomingOccasions(7);
  const { data: gifts } = useDigitalGifts();

  const upcomingOccasions = occasions?.slice(0, 3) || [];
  const recentGifts = gifts?.slice(0, 3) || [];

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🌐 التواصل الاجتماعي</h1>
          <p className="text-sm text-muted-foreground/70">شارك، تواصل، وابنِ مجتمعك السيادي</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setCreateOccasionOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            <Calendar className="w-4 h-4" />
            مناسبة
          </button>
          <button
            onClick={() => setCreatePostOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
          >
            <Plus className="w-4 h-4" />
            منشور جديد
          </button>
        </div>
      </div>

      {/* المناسبات القادمة والهدايا */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {upcomingOccasions.length > 0 && (
          <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <h3 className="text-sm font-medium text-foreground/70 flex items-center gap-2 mb-2">
              <Calendar className="w-4 h-4 text-primary" />
              مناسبات قادمة
            </h3>
            {upcomingOccasions.map((occ) => (
              <div key={occ.id} className="flex items-center justify-between p-2 rounded-xl hover:bg-white/5 text-sm">
                <span>{occ.title || occ.occasion_type}</span>
                <span className="text-xs text-muted-foreground/50">
                  {new Date(occ.occasion_date).toLocaleDateString('ar-EG')}
                </span>
              </div>
            ))}
          </div>
        )}
        {recentGifts.length > 0 && (
          <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <h3 className="text-sm font-medium text-foreground/70 flex items-center gap-2 mb-2">
              <Gift className="w-4 h-4 text-primary" />
              أحدث الهدايا
            </h3>
            {recentGifts.map((gift) => (
              <div key={gift.id} className="flex items-center justify-between p-2 rounded-xl hover:bg-white/5 text-sm">
                <span>🎁 من {gift.sender_name || `#${gift.sender_id}`}</span>
                <span className="text-xs text-muted-foreground/50">
                  {gift.gift_value_mrusdt > 0 ? `${gift.gift_value_mrusdt} MR_USDT` : 'رسالة'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* الـ Feed */}
      <div className="space-y-3">
        {posts?.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
        {posts?.length === 0 && (
          <div className="text-center py-12 text-muted-foreground/60">
            <Users className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-lg">لا توجد منشورات</p>
            <p className="text-sm">كن أول من يشارك!</p>
          </div>
        )}
      </div>

      {/* المودالات */}
      <CreatePostModal isOpen={createPostOpen} onClose={() => setCreatePostOpen(false)} />
      <CreateOccasionModal isOpen={createOccasionOpen} onClose={() => setCreateOccasionOpen(false)} />
    </div>
  );
}