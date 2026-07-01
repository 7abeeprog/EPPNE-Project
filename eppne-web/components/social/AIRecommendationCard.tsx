// components/social/AIRecommendationCard.tsx
'use client';

import { useMatchSuggestions } from '@/hooks/social/useMatchSuggestions';
import { Loader2, Sparkles, User, Heart } from 'lucide-react';

export default function AIRecommendationCard() {
  const { data: suggestions, isLoading } = useMatchSuggestions({ limit: 5 });

  if (isLoading) {
    return (
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 flex justify-center items-center h-32">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  if (!suggestions || suggestions.length === 0) {
    return (
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center text-muted-foreground/50 text-sm">
        <Sparkles className="w-8 h-8 mx-auto mb-2 text-primary/30" />
        قم بتحديث ملفك الشخصي للحصول على توصيات ذكية
      </div>
    );
  }

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
      <h4 className="text-sm font-medium text-foreground/70 flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-primary" />
        توصيات الذكاء الاصطناعي
      </h4>
      <div className="space-y-2">
        {suggestions.map((sug, idx) => (
          <div key={idx} className="flex items-center justify-between p-2 rounded-xl bg-white/5 border border-white/5">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs font-bold">
                {sug.user_name?.[0] || 'U'}
              </div>
              <div>
                <p className="text-sm font-medium text-foreground/80">{sug.user_name || `المستخدم #${sug.suggested_user_id}`}</p>
                <p className="text-xs text-muted-foreground/50">{sug.reasoning}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-primary font-medium">{sug.match_score}%</span>
              <button className="p-1.5 rounded-lg bg-primary/20 text-primary hover:bg-primary/30 transition-colors">
                <Heart className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}