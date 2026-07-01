// components/invitations/AIAssistantChat.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { useChatWithAI } from '@/hooks/invitations/useChatWithAI';
import { useInvitation } from '@/hooks/invitations/useInvitations';
import { Loader2, Send, Bot, User, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { v4 as uuidv4 } from 'uuid';

interface AIAssistantChatProps {
  invitationId: number;
  visitorSessionId: string;
  className?: string;
}

interface Message {
  id: string;
  text: string;
  isFromAI: boolean;
  timestamp: Date;
}

export default function AIAssistantChat({ invitationId, visitorSessionId, className }: AIAssistantChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      text: '👋 مرحباً! أنا مساعدك الذكي. كيف يمكنني مساعدتك اليوم؟',
      isFromAI: true,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const chatWithAI = useChatWithAI();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      text: input.trim(),
      isFromAI: false,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const idempotencyKey = `chat-${invitationId}-${uuidv4()}`;

    try {
      const response = await chatWithAI.mutateAsync({
        invitationId,
        data: {
          message: userMessage.text,
          visitor_session_id: visitorSessionId,
        },
        idempotencyKey,
      });

      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        text: response.reply,
        isFromAI: true,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        text: '⚠️ حدث خطأ في التواصل مع المساعد الذكي. يرجى المحاولة مرة أخرى.',
        isFromAI: true,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={cn("flex flex-col h-[400px] rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 overflow-hidden", className)}>
      <div className="flex items-center gap-2 p-3 border-b border-white/10 bg-primary/5">
        <Sparkles className="w-4 h-4 text-primary" />
        <span className="text-sm font-medium text-foreground/80">المساعد الذكي</span>
        <span className="text-xs text-muted-foreground/40 ml-auto">مدعوم بالذكاء الاصطناعي</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex items-start gap-2 max-w-[80%]",
              msg.isFromAI ? "self-start" : "self-end flex-row-reverse"
            )}
          >
            <div className={cn(
              "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0",
              msg.isFromAI ? "bg-primary/20 text-primary" : "bg-white/10 text-muted-foreground"
            )}>
              {msg.isFromAI ? <Bot className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
            </div>
            <div className={cn(
              "p-2.5 rounded-xl text-sm",
              msg.isFromAI
                ? "bg-white/5 border border-white/5 text-foreground/80"
                : "bg-primary/20 text-primary-foreground"
            )}>
              {msg.text}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex items-start gap-2 self-start">
            <div className="w-7 h-7 rounded-full bg-primary/20 text-primary flex items-center justify-center">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="p-2.5 rounded-xl bg-white/5 border border-white/5">
              <Loader2 className="w-4 h-4 animate-spin text-primary/60" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex gap-2 p-3 border-t border-white/10 bg-white/5">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="اكتب رسالتك..."
          className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80 placeholder:text-muted-foreground/40"
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 transition-all duration-300"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}