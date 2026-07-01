// components/sovereign-entities/KYBDocumentUploader.tsx
'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getKYBDocuments, uploadKYBDocument } from '@/services/sovereign-entities';
import { Upload, File, CheckCircle, XCircle, Loader2, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { EntityDocument } from '@/types/sovereign-entities';

interface KYBDocumentUploaderProps {
  entityId: number;
  canUpload?: boolean;
}

const documentTypes = [
  { value: 'commercial_register', label: 'السجل التجاري' },
  { value: 'tax_card', label: 'البطاقة الضريبية' },
  { value: 'authorization_letter', label: 'خطاب التفويض' },
  { value: 'identity_proof', label: 'إثبات الهوية' },
  { value: 'other', label: 'مستندات أخرى' },
];

const statusConfig = {
  PENDING: { label: 'قيد الانتظار', color: 'text-amber-500 bg-amber-500/10 border-amber-500/30' },
  APPROVED: { label: 'تم التحقق', color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30' },
  REJECTED: { label: 'مرفوض', color: 'text-red-500 bg-red-500/10 border-red-500/30' },
};

export default function KYBDocumentUploader({ entityId, canUpload = false }: KYBDocumentUploaderProps) {
  const queryClient = useQueryClient();
  const [selectedType, setSelectedType] = useState('commercial_register');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['kyb-documents', entityId],
    queryFn: () => getKYBDocuments(entityId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const uploadMutation = useMutation({
    mutationFn: (payload: { document_type: string; document_url: string }) =>
      uploadKYBDocument(entityId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kyb-documents', entityId] });
      setFile(null);
      setPreview(null);
      setIsUploading(false);
    },
    onError: () => setIsUploading(false),
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      const reader = new FileReader();
      reader.onload = (event) => setPreview(event.target?.result as string);
      reader.readAsDataURL(selected);
    }
  };

  const handleUpload = () => {
    if (!file) return;
    setIsUploading(true);
    // في الواقع، يتم رفع الملف إلى تخزين مؤقت (S3) ثم إرسال الرابط
    // تبسيطاً، سنرسل رابط وهمي
    const fakeUrl = URL.createObjectURL(file);
    uploadMutation.mutate({
      document_type: selectedType,
      document_url: fakeUrl,
    });
  };

  if (isLoading) {
    return <div className="flex justify-center p-6"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-6">
      {/* قائمة المستندات الموجودة */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-foreground/80">المستندات المرفوعة</h4>
        {data?.length === 0 ? (
          <div className="text-center text-muted-foreground/50 text-sm py-6">
            لم يتم رفع أي مستندات بعد
          </div>
        ) : (
          data?.map((doc) => {
            const status = statusConfig[doc.status as keyof typeof statusConfig] || statusConfig.PENDING;
            return (
              <div
                key={doc.id}
                className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <File className="w-4 h-4 text-muted-foreground/50" />
                  <div>
                    <p className="text-sm text-foreground/80">
                      {documentTypes.find(t => t.value === doc.document_type)?.label || doc.document_type}
                    </p>
                    <p className="text-xs text-muted-foreground/50">
                      {new Date(doc.created_at).toLocaleDateString('ar-EG')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn("text-xs px-2 py-0.5 rounded-full border", status.color)}>
                    {status.label}
                  </span>
                  {doc.document_url && (
                    <a href={doc.document_url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                      <Eye className="w-4 h-4 text-muted-foreground/50" />
                    </a>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* رافع المستندات (للمستخدمين المخولين) */}
      {canUpload && (
        <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-4">
          <h4 className="text-sm font-medium text-foreground/80">رفع مستند جديد</h4>
          
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[150px]">
              <label className="text-xs text-muted-foreground/60">نوع المستند</label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full mt-1 px-3 py-2 rounded-lg bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                {documentTypes.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            
            <div className="flex-1 min-w-[200px]">
              <label className="text-xs text-muted-foreground/60">الملف</label>
              <div className="relative mt-1">
                <input
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:bg-primary/20 file:text-primary file:text-sm"
                />
                {preview && (
                  <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-emerald-500 text-white flex items-center justify-center text-[10px]">
                    ✓
                  </div>
                )}
              </div>
            </div>
            
            <button
              onClick={handleUpload}
              disabled={!file || isUploading}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              رفع
            </button>
          </div>
        </div>
      )}
    </div>
  );
}