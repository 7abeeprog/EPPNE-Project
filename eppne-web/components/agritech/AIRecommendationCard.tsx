// components/agritech/AIRecommendationCard.tsx
'use client';

import { Sparkles, AlertTriangle, Info, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AIRecommendation } from '@/types/agritech';

interface AIRecommendationCardProps {
  recommendation: AIRecommendation;
  className?: string;
}

const priorityConfig = {
  HIGH: { color: 'border-red-500/30 bg-red-500/5 text-red-500', icon: AlertTriangle },
  MEDIUM: { color: 'border-amber-500/30 bg-amber-500/5 text-amber-500', icon: Info },
  LOW: { color: 'border-blue-500/30 bg-blue-500/5 text-blue-500', icon: CheckCircle },
};

export default function AIRecommendationCard({ recommendation, className }: AIRecommendationCardProps) {
  const config = priorityConfig[recommendation.priority];

  return (
    <div className={cn("p-4 rounded-2xl border backdrop-blur-sm bg-card/20", config.color, className)}>
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-xl bg-white/5">
          <Sparkles className="w-4 h-4 text-primary" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-foreground/80">{recommendation.title}</h4>
            <span className={cn("text-xs px-2 py-0.5 rounded-full border", config.color)}>
              {recommendation.priority}
            </span>
          </div>
          <p className="text-sm text-muted-foreground/60 mt-1">{recommendation.description}</p>
          <p className="text-xs text-muted-foreground/30 mt-1">
            {new Date(recommendation.created_at).toLocaleString('ar-EG')}
          </p>
        </div>
        <config.icon className="w-5 h-5" />
      </div>
    </div>
  );
}