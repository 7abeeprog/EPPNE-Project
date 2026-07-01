// components/zamakana/NodeCard.tsx
'use client';

import { Calendar, MapPin, Tag, Users, Lightbulb, Building2, Globe } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ZamakanaNode, ZamakanaNodeType } from '@/types/zamakana';

const typeConfig: Record<ZamakanaNodeType, { label: string; icon: React.ReactNode; color: string }> = {
  ERA: {
    label: 'حقبة',
    icon: <Calendar className="w-4 h-4" />,
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
  },
  INNOVATION: {
    label: 'ابتكار',
    icon: <Lightbulb className="w-4 h-4" />,
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
  },
  PERSON: {
    label: 'شخصية',
    icon: <Users className="w-4 h-4" />,
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
  },
  EVENT: {
    label: 'حدث',
    icon: <Globe className="w-4 h-4" />,
    color: 'border-purple-500/30 text-purple-500 bg-purple-500/5',
  },
};

export default function NodeCard({ node }: { node: ZamakanaNode }) {
  const config = typeConfig[node.node_type];

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{node.title}</h4>
          <p className="text-sm text-muted-foreground/60 line-clamp-2">{node.description}</p>
        </div>
        <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color)}>
          {config.icon}
          {config.label}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground/50">
        {node.timeline_year && (
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {node.timeline_year}
          </span>
        )}
        {node.geo_location && (
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {node.geo_location}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Tag className="w-3 h-3" />
          {node.node_type}
        </span>
      </div>
    </div>
  );
}