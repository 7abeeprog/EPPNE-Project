// components/sovereign-entities/BrandEditor.tsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getEntityPage, updateEntityPage, publishEntityPage } from '@/services/sovereign-entities';
import { Loader2, Save, Globe, CheckCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import DOMPurify from 'dompurify'; // تأكد من تثبيت المكتبة

interface BrandEditorProps {
  entityId: number;
  entityName: string;
  primaryColor: string;
}

export default function BrandEditor({ entityId, entityName, primaryColor }: BrandEditorProps) {
  const queryClient = useQueryClient();
  const [slug, setSlug] = useState('');
  const [metaTitle, setMetaTitle] = useState('');
  const [metaDescription, setMetaDescription] = useState('');
  const [structure, setStructure] = useState<any>(null);
  const [isPublishing, setIsPublishing] = useState(false);

  // جلب بيانات الصفحة
  const { data, isLoading } = useQuery({
    queryKey: ['entity-page', entityId],
    queryFn: () => getEntityPage(entityId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  // تحديث البيانات عند تحميلها
  useEffect(() => {
    if (data?.page) {
      setSlug(data.page.slug || '');
      setMetaTitle(data.page.meta_title || '');
      setMetaDescription(data.page.meta_description || '');
      setStructure(data.page.custom_structure || null);
    }
  }, [data]);

  // دالة تنظيف المحتوى (XSS Protection)
  const sanitizeContent = useCallback((content: any) => {
    if (!content) return content;
    // تنظيف النصوص داخل الـ props
    const sanitized = JSON.parse(JSON.stringify(content));
    if (sanitized.sections) {
      sanitized.sections = sanitized.sections.map((section: any) => ({
        ...section,
        components: section.components?.map((comp: any) => ({
          ...comp,
          props: {
            ...comp.props,
            // تعقيم أي نص قد يحتوي على HTML
            title: comp.props.title ? DOMPurify.sanitize(comp.props.title) : comp.props.title,
            subtitle: comp.props.subtitle ? DOMPurify.sanitize(comp.props.subtitle) : comp.props.subtitle,
            description: comp.props.description ? DOMPurify.sanitize(comp.props.description) : comp.props.description,
          }
        })) || []
      }));
    }
    return sanitized;
  }, []);

  // تحديث الصفحة
  const updateMutation = useMutation({
    mutationFn: (payload: any) => updateEntityPage(entityId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-page', entityId] });
    },
  });

  // نشر الصفحة
  const publishMutation = useMutation({
    mutationFn: () => publishEntityPage(entityId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-page', entityId] });
      setIsPublishing(false);
    },
    onError: () => setIsPublishing(false),
  });

  const handleSave = () => {
    const sanitizedStructure = sanitizeContent(structure);
    updateMutation.mutate({
      slug,
      meta_title: metaTitle,
      meta_description: metaDescription,
      custom_structure: sanitizedStructure,
    });
  };

  const handlePublish = () => {
    setIsPublishing(true);
    publishMutation.mutate();
  };

  if (isLoading) {
    return <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-6 p-4">
      {/* الهيدر */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground/90">🖌️ بناء الهوية المؤسسية</h3>
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={updateMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors disabled:opacity-50"
          >
            {updateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            حفظ
          </button>
          <button
            onClick={handlePublish}
            disabled={publishMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
          >
            {publishMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />}
            نشر
          </button>
        </div>
      </div>

      {/* حالة النشر */}
      {data?.page?.published_at && (
        <div className="flex items-center gap-2 text-xs text-emerald-500/70 bg-emerald-500/10 px-3 py-1.5 rounded-full w-fit">
          <CheckCircle className="w-3 h-3" />
          منشور منذ {new Date(data.page.published_at).toLocaleDateString('ar-EG')}
        </div>
      )}

      {/* الحقول */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium text-foreground/80">المسار (Slug) *</label>
          <input
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/\s/g, '-'))}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            placeholder="ministry-of-agriculture"
          />
          <p className="text-xs text-muted-foreground/40 mt-1">
            الرابط: /sovereign-entities/public/{slug || '...'}
          </p>
        </div>
        <div>
          <label className="text-sm font-medium text-foreground/80">العنوان (Meta Title)</label>
          <input
            type="text"
            value={metaTitle}
            onChange={(e) => setMetaTitle(e.target.value)}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            placeholder="عنوان الصفحة لتحسين محركات البحث"
          />
        </div>
        <div className="md:col-span-2">
          <label className="text-sm font-medium text-foreground/80">الوصف (Meta Description)</label>
          <textarea
            value={metaDescription}
            onChange={(e) => setMetaDescription(e.target.value)}
            rows={2}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
            placeholder="وصف مختصر للصفحة"
          />
        </div>
      </div>

      {/* محرر الهيكل (JSON مبسط) – سيتم استبداله بـ Drag & Drop مستقبلاً */}
      <div>
        <label className="text-sm font-medium text-foreground/80">هيكل الصفحة (JSON)</label>
        <textarea
          value={JSON.stringify(structure, null, 2)}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              setStructure(parsed);
            } catch {
              // تجاهل الأخطاء أثناء الكتابة
            }
          }}
          rows={10}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono resize-y"
        />
        <p className="text-xs text-muted-foreground/40 mt-1">
          ⚠️ تأكد من صيغة JSON. سيتم تعقيم المحتوى تلقائياً.
        </p>
      </div>

      {/* معاينة سريعة */}
      {structure && (
        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
          <h4 className="text-sm font-medium text-foreground/70 mb-2">👁️ معاينة سريعة</h4>
          <div className="space-y-2 text-sm">
            {structure.sections?.map((section: any, idx: number) => (
              <div key={idx} className="p-3 rounded-lg bg-white/5">
                <p className="text-foreground/80 font-medium">{section.components?.[0]?.props?.title || 'قسم'}</p>
                <p className="text-muted-foreground/60 text-xs">{section.components?.[0]?.props?.subtitle || ''}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}