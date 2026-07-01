import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { translationService } from '@/services/translation.service';
import { useTranslationStore } from '@/store/translation-store';
import { LanguageSelector } from './LanguageSelector';
import { ChatTranslateResponse } from '@/types/translation';

export function ChatTranslator() {
  const { targetLang, setTargetLang, conversationId, generateNewConversationId } = useTranslationStore();
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState<ChatTranslateResponse[]>([]);

  const { mutate, isPending } = useMutation({
    mutationFn: translationService.chatTranslate,
    onSuccess: (data) => setHistory((prev) => [...prev, data]),
  });

  const handleSend = () => {
    if (!message.trim()) return;
    mutate({ message, conversation_id: conversationId, target_lang: targetLang });
    setMessage('');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <LanguageSelector value={targetLang} onChange={setTargetLang} label="لغة الهدف" showAuto={false} />
        <button
          onClick={generateNewConversationId}
          className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white/70 text-sm hover:bg-white/10 transition-all"
        >
          ↻ محادثة جديدة
        </button>
        <span className="text-xs text-white/30">ID: {conversationId.slice(0, 8)}...</span>
      </div>

      <div className="h-60 overflow-y-auto space-y-3 p-3 bg-white/5 rounded-xl border border-white/10">
        {history.length === 0 && <p className="text-white/30 text-center mt-20">ابدأ المحادثة الآن...</p>}
        {history.map((item, idx) => (
          <div key={idx} className="glass-card p-3 rounded-xl border border-white/10 space-y-1">
            <p className="text-white/60 text-xs">🗣️ {item.original}</p>
            <p className="text-white font-medium">🤖 {item.translated}</p>
          </div>
        ))}
        {isPending && <div className="text-white/50 text-sm">يجري الترجمة...</div>}
      </div>

      <div className="flex gap-3">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="اكتب رسالتك هنا..."
          className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white 
                     focus:border-neon-blue outline-none transition-all"
          dir="auto"
        />
        <button
          onClick={handleSend}
          disabled={isPending || !message.trim()}
          className="px-6 py-3 bg-neon-blue rounded-xl text-white font-bold hover:scale-105 transition-all disabled:opacity-50"
        >
          إرسال
        </button>
      </div>
    </div>
  );
}