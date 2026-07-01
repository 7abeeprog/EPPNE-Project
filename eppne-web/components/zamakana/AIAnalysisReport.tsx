// components/zamakana/AIAnalysisReport.tsx
'use client';

import { Brain, TrendingUp, Leaf, Users, Lightbulb } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AIAnalysisReportProps {
  report: Record<string, any>;
  className?: string;
}

export default function AIAnalysisReport({ report, className }: AIAnalysisReportProps) {
  const sections = [
    { key: 'economic_impact', label: 'التأثير الاقتصادي', icon: TrendingUp, color: 'text-emerald-500' },
    { key: 'environmental_impact', label: 'التأثير البيئي', icon: Leaf, color: 'text-green-500' },
    { key: 'social_impact', label: 'التأثير الاجتماعي', icon: Users, color: 'text-blue-500' },
  ];

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center gap-2 mb-3">
        <Brain className="w-5 h-5 text-primary" />
        <h4 className="text-sm font-medium text-foreground/80">تقرير تحليل الذكاء الاصطناعي</h4>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {sections.map((section) => (
          <div key={section.key} className="p-3 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center gap-2">
              <section.icon className={cn("w-4 h-4", section.color)} />
              <span className="text-xs text-muted-foreground/50">{section.label}</span>
            </div>
            <p className="mt-1 text-sm text-foreground/70">
              {report[section.key] || 'غير متوفر'}
            </p>
          </div>
        ))}
      </div>

      {report.recommendations && report.recommendations.length > 0 && (
        <div className="p-3 rounded-xl bg-white/5 border border-white/10">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-500" />
            <span className="text-xs text-muted-foreground/50">التوصيات</span>
          </div>
          <ul className="mt-1 space-y-1">
            {report.recommendations.map((rec: string, idx: number) => (
              <li key={idx} className="text-sm text-foreground/70 flex items-start gap-2">
                <span className="text-primary/50">•</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.error && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500/70 text-sm">
          ⚠️ {report.error}
        </div>
      )}
    </div>
  );
}