import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { translationService } from '@/services/translation.service';
import { useTranslationStore } from '@/store/translation-store';
import { LanguageSelector } from './LanguageSelector';
import { TranslateResponse } from '@/types/translation';

export function TextTranslator() {
  const { sourceLang, targetLang, setSourceLang, setTargetLang } = useTranslationStore();
  const [inputText, setInputText] = useState('');
  const [result, setResult] = useState<TranslateResponse | null>(null);

  const { mutate, isPending, error } = useMutation({
    mutationFn: translationService.translate,
    onSuccess: (data) => setResult(data),
    onError: (err) => console.error('Translation failed:', err),
  });

  const handleTranslate = () => {
    if (!inputText.trim()) return;
    mutate({
      text: inputText,
      source_lang: sourceLang,
      target_lang: targetLang,
      context: 'general',
    });
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <LanguageSelector value={sourceLang} onChange={setSourceLang} label="لغة المصدر" showAuto />
        <LanguageSelector value={targetLang} onChange={setTargetLang} label="لغة الهدف" showAuto={false} />
      </div>

      <div className="relative">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="أدخل النص الذي تريد ترجمته..."
          className="w-full h-32 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white 
                     focus:border-neon-blue focus:ring-1 focus:ring-neon-blue transition-all
                     backdrop-blur-sm outline-none resize-none"
          dir="auto"
        />
        <button
          onClick={handleTranslate}
          disabled={isPending || !inputText.trim()}
          className="absolute bottom-3 left-3 px-6 py-2 bg-gradient-to-r from-neon-blue to-neon-purple 
                     rounded-lg text-white font-bold shadow-lg shadow-neon-blue/20 
                     hover:scale-105 transition-all disabled:opacity-50 disabled:hover:scale-100"
        >
          {isPending ? 'جارٍ الترجمة...' : 'ترجم'}
        </button>
      </div>

      {error && <div className="text-red-400 text-sm bg-red-500/10 p-3 rounded-xl border border-red-500/20">حدث خطأ أثناء الترجمة.</div>}

      {result && (
        <div className="glass-card p-4 rounded-xl border border-white/10 space-y-2">
          <div className="flex justify-between text-xs text-white/50">
            <span>من: {result.source_lang} → إلى: {result.target_lang}</span>
            <span>{result.from_cache ? '✅ من الذاكرة المؤقتة' : '🌐 ترجمة مباشرة'}</span>
            <span>التكلفة: {result.cost_mrusdt} MRUSDT</span>
          </div>
          <p className="text-lg text-white leading-relaxed whitespace-pre-wrap">{result.translated_text}</p>
        </div>
      )}
    </div>
  );
}