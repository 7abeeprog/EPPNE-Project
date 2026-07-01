// components/ui/ConfirmationModal.tsx
'use client';

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText: string;
  cancelText?: string;
  type?: 'danger' | 'warning' | 'info';
  entityName?: string; // لطلب كتابة الاسم
  primaryColor?: string; // لتمييز الـ Modal بلون الكيان
  requiresTyping?: boolean;
}

export default function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText,
  cancelText = 'إلغاء',
  type = 'danger',
  entityName,
  primaryColor = '#8CC63F',
  requiresTyping = false,
}: ConfirmationModalProps) {
  const [typedText, setTypedText] = useState('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (!isOpen) {
      setTypedText('');
    }
  }, [isOpen]);

  if (!mounted || !isOpen) return null;

  const isTypingValid = !requiresTyping || typedText === entityName;

  const typeStyles = {
    danger: 'border-red-500/30 shadow-[0_0_50px_rgba(239,68,68,0.15)]',
    warning: 'border-amber-500/30 shadow-[0_0_50px_rgba(245,158,11,0.15)]',
    info: 'border-blue-500/30 shadow-[0_0_50px_rgba(59,130,246,0.15)]',
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className={cn(
          "relative w-full max-w-md p-6 rounded-2xl bg-card/80 backdrop-blur-3xl border",
          "animate-in zoom-in-95 duration-200",
          typeStyles[type]
        )}
        style={{
          borderColor: primaryColor + '40',
          boxShadow: `0 0 80px -20px ${primaryColor}40`,
        }}
      >
        {/* شريط علوي بلون الكيان */}
        <div
          className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl"
          style={{ backgroundColor: primaryColor }}
        />

        {/* زر الإغلاق */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors"
        >
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        {/* الأيقونة */}
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className={cn(
            "w-6 h-6",
            type === 'danger' ? 'text-red-500' : type === 'warning' ? 'text-amber-500' : 'text-blue-500'
          )} />
          <h3 className="text-lg font-bold text-foreground/90">{title}</h3>
        </div>

        {/* الرسالة */}
        <p className="text-sm text-foreground/70 leading-relaxed mb-4">{message}</p>

        {/* حقل كتابة التأكيد */}
        {requiresTyping && entityName && (
          <div className="mb-4">
            <p className="text-xs text-muted-foreground/60 mb-2">
              اكتب <span className="font-medium text-foreground/80">{entityName}</span> للتأكيد
            </p>
            <input
              type="text"
              value={typedText}
              onChange={(e) => setTypedText(e.target.value)}
              placeholder={`اكتب "${entityName}"`}
              className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
        )}

        {/* الأزرار */}
        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors text-sm text-foreground/70"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={!isTypingValid}
            className={cn(
              "flex-1 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300",
              type === 'danger' 
                ? "bg-red-500 text-white hover:bg-red-600 shadow-[0_0_30px_rgba(239,68,68,0.3)]" 
                : "bg-primary text-primary-foreground shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)]",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}