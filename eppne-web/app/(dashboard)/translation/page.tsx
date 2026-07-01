'use client'; // نظراً لاستخدام Zustand و TanStack Query

import { useState } from 'react';
import { TextTranslator } from '@/components/translation/TextTranslator';
import { BatchTranslator } from '@/components/translation/BatchTranslator';
import { ChatTranslator } from '@/components/translation/ChatTranslator';
import { useTranslationStore } from '@/store/translation-store';

export default function TranslationPage() {
  const { activeTab, setActiveTab } = useTranslationStore();

  const tabs = [
    { id: 'single', label: '📝 ترجمة نصية', component: <TextTranslator /> },
    { id: 'batch', label: '📚 ترجمة جماعية', component: <BatchTranslator /> },
    { id: 'chat', label: '💬 مترجم المحادثات', component: <ChatTranslator /> },
  ];

  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto">
      {/* الهوية البصرية: العنوان بتوهج نيون */}
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-neon-blue to-neon-purple bg-clip-text text-transparent">
          المترجم الشامل 🌐
        </h1>
        <p className="text-white/50 mt-2">ترجمة فورية مع ذاكرة مؤقتة وتكامل مالي لحظي</p>
      </div>

      {/* علامات التبويب (Glassmorphism) */}
      <div className="flex flex-wrap gap-2 p-1 glass-card rounded-2xl border border-white/10 mb-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex-1 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300
              ${activeTab === tab.id 
                ? 'bg-gradient-to-r from-neon-blue/30 to-neon-purple/30 text-white shadow-lg shadow-neon-blue/10' 
                : 'text-white/40 hover:text-white/80 hover:bg-white/5'
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* عرض المحتوى حسب التاب المختار */}
      <div className="glass-card p-6 rounded-2xl border border-white/10 backdrop-blur-xl">
        {tabs.find(t => t.id === activeTab)?.component}
      </div>
    </div>
  );
}