import apiClient from '@/lib/axios'; // افترض وجود عميل Axios مسبق الإعداد
import {
  TranslateRequest,
  TranslateResponse,
  BatchTranslateRequest,
  ChatTranslateRequest,
  ChatTranslateResponse,
  SupportedLanguage,
} from '@/types/translation';

// دالة مساعدة لتوليد Idempotency Key بناءً على المحتوى (لتجنب تكرار الطلبات)
async function generateIdempotencyKey(text: string, target: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(`${text}:${target}`);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export const translationService = {
  // 1. الترجمة الفردية
  translate: async (request: TranslateRequest): Promise<TranslateResponse> => {
    // توليد مفتاح التكرار تلقائياً (Idempotency) لتخفيف الضغط عن الخادم
    const key = await generateIdempotencyKey(request.text, request.target_lang);
    const payload = { ...request, idempotency_key: key };
    const response = await apiClient.post<TranslateResponse>('/translation/translate', payload);
    return response.data;
  },

  // 2. الترجمة الجماعية
  batchTranslate: async (request: BatchTranslateRequest): Promise<string[]> => {
    const response = await apiClient.post<string[]>('/translation/batch-translate', request);
    return response.data;
  },

  // 3. ترجمة المحادثات
  chatTranslate: async (request: ChatTranslateRequest): Promise<ChatTranslateResponse> => {
    const response = await apiClient.post<ChatTranslateResponse>('/translation/chat-translate', request);
    return response.data;
  },

  // 4. جلب اللغات المدعومة
  getSupportedLanguages: async (): Promise<SupportedLanguage[]> => {
    const response = await apiClient.get<SupportedLanguage[]>('/translation/languages');
    return response.data;
  },
};