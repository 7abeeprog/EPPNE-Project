// لا مجال لـ any هنا، كل شيء محدد بدقة (وفقاً للمحادثة الثانية)
export interface SupportedLanguage {
  code: string;
  name: string;
  native_name: string | null;
}

export interface TranslateRequest {
  text: string;
  source_lang?: string; // "auto" افتراضياً
  target_lang: string;
  context?: string;
  idempotency_key?: string; // سيتم توليده تلقائياً في الخدمة
}

export interface TranslateResponse {
  translated_text: string;
  source_lang: string;
  target_lang: string;
  from_cache: boolean;
  cost_mrusdt: string;
}

export interface BatchTranslateRequest {
  texts: string[];
  source_lang?: string;
  target_lang: string;
}

export interface ChatTranslateRequest {
  message: string;
  conversation_id: string;
  target_lang: string;
}

export interface ChatTranslateResponse {
  original: string;
  translated: string;
  target_lang: string;
}