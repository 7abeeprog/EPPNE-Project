import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { translationService } from '@/services/translation.service';
import { SupportedLanguage } from '@/types/translation';

interface LanguageSelectorProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  showAuto?: boolean;
}

export function LanguageSelector({ value, onChange, label, showAuto = true }: LanguageSelectorProps) {
  const { data: languages = [], isLoading } = useQuery({
    queryKey: ['supported-languages'],
    queryFn: translationService.getSupportedLanguages,
    staleTime: 1000 * 60 * 60, // ساعة كاملة (لتخفيف الضغط)
  });

  // استخدام useMemo لتصفية القائمة وإضافة "تلقائي" (تجنب إعادة الحساب)
  const options = useMemo(() => {
    const list: { code: string; name: string }[] = [];
    if (showAuto) {
      list.push({ code: 'auto', name: '🔍 تلقائي (Auto)' });
    }
    languages.forEach((lang: SupportedLanguage) => {
      list.push({ code: lang.code, name: `${lang.native_name || lang.name} (${lang.code})` });
    });
    return list;
  }, [languages, showAuto]);

  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm text-white/70 font-medium">{label}</label>}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white 
                   focus:border-neon-blue focus:ring-1 focus:ring-neon-blue transition-all
                   backdrop-blur-sm appearance-none outline-none"
        disabled={isLoading}
      >
        {options.map((opt) => (
          <option key={opt.code} value={opt.code} className="bg-gray-900 text-white">
            {opt.name}
          </option>
        ))}
      </select>
    </div>
  );
}