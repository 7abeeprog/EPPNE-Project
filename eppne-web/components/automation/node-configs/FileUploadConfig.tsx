// components/automation/node-configs/FileUploadConfig.tsx
'use client';

interface FileUploadConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function FileUploadConfig({ config, onChange }: FileUploadConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">مصدر الملف (Source)</label>
        <input
          type="text"
          value={config.source || ''}
          onChange={(e) => onChange('source', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder="{{node_1.output}} أو https://example.com/file.pdf"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          يمكن أن يكون نصاً، مرجعاً لعقدة، أو رابط HTTP
        </p>
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">اسم الملف (Filename)</label>
        <input
          type="text"
          value={config.filename || ''}
          onChange={(e) => onChange('filename', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
          placeholder="report-{{date}}.pdf"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">الوجهة (Destination)</label>
        <input
          type="text"
          value={config.destination || ''}
          onChange={(e) => onChange('destination', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder="s3://my-bucket/reports/ أو minio://bucket/folder/"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          يدعم S3 و MinIO وأنظمة الملفات المحلية
        </p>
      </div>
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-xs text-muted-foreground/60 cursor-pointer">
          <input
            type="checkbox"
            checked={config.make_public || false}
            onChange={(e) => onChange('make_public', e.target.checked)}
            className="w-4 h-4 rounded border-white/20 bg-white/5"
          />
          جعل الملف عاماً (Public)
        </label>
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">المفتاح لحفظ رابط الملف في السياق</label>
        <input
          type="text"
          value={config.save_url_to || 'file_url'}
          onChange={(e) => onChange('save_url_to', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder="file_url"
        />
      </div>
    </div>
  );
}