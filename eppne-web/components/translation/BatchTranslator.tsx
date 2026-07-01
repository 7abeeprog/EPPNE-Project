import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { translationService } from '@/services/translation.service';
import { useTranslationStore } from '@/store/translation-store';
import { LanguageSelector } from './LanguageSelector';

export function BatchTranslator() {
  const { targetLang, setTargetLang } = useTranslationStore();
  const [texts, setTexts] = useState('');
  const [results, setResults] = useState<string[] | null>(null);

  const { mutate, isPending } = useMutation({
    mutationFn: translationService.batchTranslate,
    onSuccess: (data) => setResults(data),
  });

  const handleTranslate = () => {
    const list = texts.split('\n').filter(t => t.trim().length > 0);
    if (list.length === 0) return;
    mutate({ texts: list, target_lang: targetLang, source_lang: 'auto' });
  };

  return (
    <div className="space-y-6">
      <LanguageSelector value={targetLang} onChange={setTargetLang} label="لغة الهدف" showAuto={false} />

      <textarea
        value={texts}
        onChange={(e) => setTexts(e.target.value)}
        placeholder="أدخل النصوص للترجمة (كل سطر نص منفصل)..."
        className="w-full h-40 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white 
                   focus:border-neon-blue transition-all outline-none resize-none"
        dir="auto"
      />

      <button
        onClick={handleTranslate}
        disabled={isPending || !texts.trim()}
        className="w-full py-3 bg-gradient-to-r from-neon-blue to-neon-purple rounded-xl 
                   text-white font-bold shadow-lg shadow-neon-blue/20 hover:scale-[1.02] transition-all
                   disabled:opacity-50"
      >
        {isPending ? 'جارٍ الترجمة الجماعية...' : 'ترجمة الكل'}
      </button>

      {results && (
        <div className="space-y-2">
          {results.map((res, idx) => (
            <div key={idx} className="glass-card p-3 rounded-xl border border-white/10">
              <p className="text-white text-sm">{res}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}