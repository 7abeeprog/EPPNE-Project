// components/agritech/HarvestBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { Shield, Globe, Building2, Leaf, Recycle } from 'lucide-react';
import type { HarvestGrade } from '@/types/agritech';

interface HarvestBadgeProps {
  grade: HarvestGrade;
  className?: string;
  showLabel?: boolean;
}

const gradeConfig: Record<HarvestGrade, { label: string; color: string; icon: React.ReactNode }> = {
  GRADE_1_EXPORT: {
    label: 'تصدير',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <Globe className="w-3.5 h-3.5" />,
  },
  GRADE_2_LOCAL: {
    label: 'سوق محلي',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Building2 className="w-3.5 h-3.5" />,
  },
  GRADE_3_PROCESSING: {
    label: 'تصنيع',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Shield className="w-3.5 h-3.5" />,
  },
  GRADE_4_FODDER: {
    label: 'أعلاف',
    color: 'border-purple-500/30 text-purple-500 bg-purple-500/5',
    icon: <Leaf className="w-3.5 h-3.5" />,
  },
  WASTE_SMART_BIO: {
    label: 'طاقة حيوية',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <Recycle className="w-3.5 h-3.5" />,
  },
};

export default function HarvestBadge({ grade, className, showLabel = true }: HarvestBadgeProps) {
  const config = gradeConfig[grade];

  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", config.color, className)}>
      {config.icon}
      {showLabel && config.label}
    </span>
  );
}