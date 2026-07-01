import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface TranslationUIState {
  sourceLang: string;
  targetLang: string;
  conversationId: string;
  activeTab: 'single' | 'batch' | 'chat';
  
  setSourceLang: (lang: string) => void;
  setTargetLang: (lang: string) => void;
  setActiveTab: (tab: 'single' | 'batch' | 'chat') => void;
  generateNewConversationId: () => void;
}

export const useTranslationStore = create<TranslationUIState>()(
  persist(
    (set) => ({
      sourceLang: 'auto',
      targetLang: 'en',
      conversationId: crypto.randomUUID?.() || Math.random().toString(36),
      activeTab: 'single',

      setSourceLang: (lang) => set({ sourceLang: lang }),
      setTargetLang: (lang) => set({ targetLang: lang }),
      setActiveTab: (tab) => set({ activeTab: tab }),
      generateNewConversationId: () => set({ conversationId: crypto.randomUUID?.() || Math.random().toString(36) }),
    }),
    {
      name: 'translation-storage', // حفظ التفضيلات في LocalStorage (مثل اللغة المفضلة)
      partialize: (state) => ({ sourceLang: state.sourceLang, targetLang: state.targetLang }),
    }
  )
);