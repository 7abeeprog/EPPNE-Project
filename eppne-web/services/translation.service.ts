// services/translation.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type TranslateRequest = components['schemas']['TranslateRequest'];
type TranslateResponse = components['schemas']['TranslateResponse'];
type BatchTranslateRequest = components['schemas']['BatchTranslateRequest'];
type ChatTranslateRequest = components['schemas']['ChatTranslateRequest'];
type ChatTranslateResponse = components['schemas']['ChatTranslateResponse'];
type SupportedLanguageResponse = components['schemas']['SupportedLanguageResponse'];

export const TranslationService = {
  // ==========================================
  // 1. الترجمة الفردية
  // ==========================================
  /**
   * ترجمة نص فردي
   * POST /translation/translation/translate
   * تدعم X-Tenant-ID
   */
  translate: async (data: TranslateRequest, headers?: { 'X-Tenant-ID'?: number }): Promise<TranslateResponse> => {
    try {
      const finalData = { ...data };
      if (!finalData.idempotency_key) {
        finalData.idempotency_key = generateIdempotencyKey();
      }
      const { data: result } = await apiClient.post<TranslateResponse>("/translation/translation/translate", finalData, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل الترجمة");
    }
  },

  // ==========================================
  // 2. الترجمة الجماعية
  // ==========================================
  /**
   * ترجمة نصوص متعددة دفعة واحدة
   * POST /translation/translation/batch-translate
   * تدعم X-Tenant-ID
   */
  batchTranslate: async (data: BatchTranslateRequest, headers?: { 'X-Tenant-ID'?: number }): Promise<string[]> => {
    try {
      const { data: result } = await apiClient.post<string[]>("/translation/translation/batch-translate", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل الترجمة الجماعية");
    }
  },

  // ==========================================
  // 3. ترجمة المحادثات
  // ==========================================
  /**
   * ترجمة محادثة (مع سياق)
   * POST /translation/translation/chat-translate
   * تدعم X-Tenant-ID
   */
  chatTranslate: async (data: ChatTranslateRequest, headers?: { 'X-Tenant-ID'?: number }): Promise<ChatTranslateResponse> => {
    try {
      const { data: result } = await apiClient.post<ChatTranslateResponse>("/translation/translation/chat-translate", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل ترجمة المحادثة");
    }
  },

  // ==========================================
  // 4. اللغات المدعومة
  // ==========================================
  /**
   * جلب قائمة اللغات المدعومة
   * GET /translation/translation/languages
   */
  getSupportedLanguages: async (): Promise<SupportedLanguageResponse[]> => {
    try {
      const { data } = await apiClient.get<SupportedLanguageResponse[]>("/translation/translation/languages");
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب اللغات المدعومة");
    }
  },
};