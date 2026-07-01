// components/social/GroupCard.tsx
'use client';

import { useJoinGroup, useLeaveGroup } from '@/hooks/social/useGroups';
import { Users, Lock, Globe, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SocialGroup } from '@/types/social';

interface GroupCardProps {
  group: SocialGroup;
  onJoin?: () => void;
}

export default function GroupCard({ group, onJoin }: GroupCardProps) {
  const joinGroup = useJoinGroup();
  const leaveGroup = useLeaveGroup();

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{group.name}</h4>
          <p className="text-sm text-muted-foreground/60">{group.description}</p>
          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground/50">
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {group.member_count || 0} عضو
            </span>
            <span className="flex items-center gap-1">
              {group.privacy === 'PUBLIC' ? <Globe className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
              {group.privacy}
            </span>
          </div>
        </div>
        {group.is_member ? (
          <button
            onClick={() => leaveGroup.mutate(group.id)}
            disabled={leaveGroup.isPending}
            className="px-3 py-1.5 rounded-xl text-xs border-red-500/30 text-red-500 hover:bg-red-500/10 transition-colors"
          >
            {leaveGroup.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : 'مغادرة'}
          </button>
        ) : (
          <button
            onClick={() => joinGroup.mutate(group.id, { onSuccess: onJoin })}
            disabled={joinGroup.isPending}
            className="px-3 py-1.5 rounded-xl text-xs bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            {joinGroup.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : 'انضمام'}
          </button>
        )}
      </div>
    </div>
  );
}