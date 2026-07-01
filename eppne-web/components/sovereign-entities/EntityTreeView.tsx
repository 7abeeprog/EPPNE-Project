// components/sovereign-entities/EntityTreeView.tsx
'use client';

import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ChevronDown, ChevronLeft, Building2, Layers, Users, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getEntityTree } from '@/services/sovereign-entities';
import type { EntityTreeItem } from '@/types/sovereign-entities';

interface TreeProps {
  entityId: number;
  className?: string;
}

const entityIcons = {
  STATE_GOVERNMENT: <Building2 className="w-4 h-4" />,
  MINISTRY_AUTHORITY: <Building2 className="w-4 h-4" />,
  INTERNATIONAL_ORGANIZATION: <Building2 className="w-4 h-4" />,
  MULTINATIONAL_CORP: <Building2 className="w-4 h-4" />,
  ENTERPRISE: <Building2 className="w-4 h-4" />,
  DIVISION: <Layers className="w-4 h-4" />,
  TEAM: <Users className="w-4 h-4" />,
};

function TreeNode({ node, level = 0 }: { node: EntityTreeItem; level?: number }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasChildren = node.children && node.children.length > 0;

  // إذا لم يكن هناك أبناء، نعرض العقدة فقط
  if (!hasChildren) {
    return (
      <Link
        href={`/sovereign-entities/${node.id}`}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-200",
          "hover:bg-white/10 text-foreground/80 hover:text-foreground",
          "border-l-2 border-transparent hover:border-primary/30"
        )}
        style={{ paddingLeft: `${level * 1.5 + 0.75}rem` }}
      >
        {entityIcons[node.entity_type] || <Building2 className="w-4 h-4" />}
        <span className="text-sm">{node.name}</span>
      </Link>
    );
  }

  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "flex items-center gap-2 w-full px-3 py-1.5 rounded-lg transition-all duration-200",
          "hover:bg-white/10 text-foreground/80 hover:text-foreground",
          "border-l-2 border-transparent hover:border-primary/30",
          isExpanded && "border-primary/50 text-foreground"
        )}
        style={{ paddingLeft: `${level * 1.5 + 0.75}rem` }}
      >
        {entityIcons[node.entity_type] || <Building2 className="w-4 h-4" />}
        <span className="text-sm flex-1 text-right">{node.name}</span>
        <span className="text-xs text-muted-foreground/50">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </span>
      </button>

      {isExpanded && (
        <div className="space-y-0.5">
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function EntityTreeView({ entityId, className }: TreeProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['entity-tree', entityId],
    queryFn: () => getEntityTree(entityId).then(res => res.data),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-32">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center text-red-500/70 text-sm p-4">
        حدث خطأ في تحميل الهيكل التنظيمي
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center text-muted-foreground/60 text-sm p-4">
        لا توجد هيكلية تنظيمية مسجلة
      </div>
    );
  }

  return (
    <div className={cn("space-y-0.5 p-2 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/5", className)}>
      <TreeNode node={data} level={0} />
    </div>
  );
}