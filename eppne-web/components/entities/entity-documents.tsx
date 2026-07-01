// components/entities/entity-documents.tsx
"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { UploadCloud, FileText, CheckCircle, XCircle, Clock, ExternalLink, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

// 🟢 الترقية المعمارية: استيراد محركات TanStack
import { useEntityDetails, useEntityMutations } from "@/hooks/use-entities";

interface EntityDocumentsProps {
  entityId: number;
}

const documentTypeLabels: Record<string, string> = {
  commercial_register: "السجل التجاري",
  tax_card: "البطاقة الضريبية",
  authorization_letter: "خطاب التفويض",
  other: "أخرى",
};

// 🟢 توحيد الشارات مع النيون الزجاجي
const statusConfig: Record<string, { label: string; color: string; icon: any }> = {
  PENDING: { label: "قيد المراجعة", color: "bg-amber-500/10 border-amber-500/30 text-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.2)]", icon: Clock },
  APPROVED: { label: "معتمد سيادياً", color: "bg-emerald-500/10 border-emerald-500/30 text-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.2)]", icon: ShieldCheck },
  REJECTED: { label: "مرفوض", color: "bg-red-500/10 border-red-500/30 text-red-500 shadow-[0_0_10px_rgba(239,68,68,0.2)]", icon: XCircle },
};

export function EntityDocuments({ entityId }: EntityDocumentsProps) {
  // 🟢 1. جلب البيانات تلقائياً (بدون useEffect)
  const { documents = [], isLoading } = useEntityDetails(entityId);
  // 🟢 2. جلب محرك الرفع
  const { uploadDocument } = useEntityMutations(entityId);

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [documentType, setDocumentType] = useState("commercial_register");
  const [documentUrl, setDocumentUrl] = useState("");

  const handleUpload = () => {
    if (!documentUrl) {
      toast.error("يرجى إدخال رابط المستند المشفر");
      return;
    }
    
    // 🟢 الهوك يتولى إرسال البيانات وعرض الإشعار (Toast) وتحديث الكاش
    uploadDocument.mutate({
      document_type: documentType,
      document_url: documentUrl,
    }, {
      onSuccess: () => {
        setIsDialogOpen(false);
        setDocumentUrl("");
        setDocumentType("commercial_register");
      }
    });
  };

  return (
    <div className="w-full rounded-[2rem] border border-white/10 bg-card/30 backdrop-blur-xl shadow-lg relative overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* إضاءة خلفية نيون */}
      <div className="absolute top-0 left-0 w-64 h-64 bg-primary/10 blur-[80px] rounded-full pointer-events-none opacity-50" />

      {/* 🟢 الرأس السيادي */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 md:p-8 border-b border-white/5 bg-background/20 relative z-10">
        <div>
          <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
            <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20 shadow-inner">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            مستندات التحقق (KYB)
          </h2>
          <p className="mt-2 text-sm text-muted-foreground font-medium">
            المستندات القانونية المشفرة لإثبات هوية الكيان
          </p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="font-bold rounded-xl shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-all">
              <UploadCloud className="ml-2 h-5 w-5" />
              رفع مستند سيادي
            </Button>
          </DialogTrigger>
          
          {/* 🟢 النافذة المنبثقة الزجاجية */}
          <DialogContent className="sm:max-w-[450px] bg-background/80 backdrop-blur-2xl border-white/10 shadow-[0_0_50px_rgba(var(--primary-rgb),0.15)] rounded-[2rem] p-6">
            <DialogHeader>
              <DialogTitle className="text-xl font-black text-foreground flex items-center gap-2">
                <UploadCloud className="h-5 w-5 text-primary" /> رفع مستند جديد
              </DialogTitle>
              <DialogDescription className="font-medium text-muted-foreground">
                أضف رابط المستند الرسمي لرفعه إلى شبكة التدقيق
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-5 py-4">
              <div className="space-y-3">
                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">نوع المستند</Label>
                <Select onValueChange={setDocumentType} defaultValue="commercial_register">
                  <SelectTrigger className="h-12 bg-background/50 border-white/10 focus:ring-primary rounded-xl font-bold">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl border-white/10 backdrop-blur-2xl bg-card/90">
                    {Object.entries(documentTypeLabels).map(([value, label]) => (
                      <SelectItem key={value} value={value} className="font-medium">{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-3">
                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">رابط المستند السري</Label>
                <Input
                  placeholder="https://..."
                  value={documentUrl}
                  onChange={(e) => setDocumentUrl(e.target.value)}
                  className="h-12 bg-background/50 border-white/10 focus-visible:ring-primary rounded-xl"
                  dir="ltr"
                />
                <p className="text-[11px] font-medium text-muted-foreground/70 bg-primary/5 p-2 rounded-lg border border-primary/10">
                  يفضل استخدام روابط IPFS اللامركزية لضمان سيادة البيانات.
                </p>
              </div>
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="ghost" onClick={() => setIsDialogOpen(false)} className="rounded-xl hover:bg-destructive/10 hover:text-destructive">إلغاء</Button>
              <Button onClick={handleUpload} disabled={uploadDocument.isPending} className="rounded-xl font-bold shadow-lg w-full sm:w-auto">
                {uploadDocument.isPending ? "جاري التشفير..." : "اعتماد ورفع"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* 🟢 محتوى الجدول الزجاجي */}
      <div className="p-0 md:p-4 relative z-10">
        <div className="rounded-2xl border border-white/5 bg-background/30 overflow-hidden shadow-inner">
          <Table>
            <TableHeader className="bg-background/40">
              <TableRow className="border-white/5 hover:bg-transparent">
                <TableHead className="font-bold text-muted-foreground">نوع المستند</TableHead>
                <TableHead className="font-bold text-muted-foreground">الرابط المرجعي</TableHead>
                <TableHead className="font-bold text-muted-foreground">حالة التدقيق</TableHead>
                <TableHead className="font-bold text-muted-foreground">تاريخ الرفع</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-12">
                    <UploadCloud className="h-8 w-8 mx-auto mb-3 text-primary/40 animate-pulse" />
                    <p className="text-sm font-bold text-muted-foreground">جاري فك تشفير المستندات...</p>
                  </TableCell>
                </TableRow>
              ) : documents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-16">
                    <FileText className="h-10 w-10 mx-auto mb-4 text-muted-foreground/30" />
                    <p className="text-lg font-black text-foreground/70 mb-1">لا توجد مستندات مرفوعة</p>
                    <p className="text-sm text-muted-foreground font-medium">الكيان بانتظار إثبات هويته القانونية</p>
                  </TableCell>
                </TableRow>
              ) : (
                documents.map((doc: any) => {
                  const status = statusConfig[doc.status] || statusConfig.PENDING;
                  const StatusIcon = status.icon;

                  return (
                    <TableRow key={doc.id} className="border-white/5 hover:bg-primary/5 transition-colors group">
                      <TableCell className="font-bold">
                        {documentTypeLabels[doc.document_type] || doc.document_type}
                      </TableCell>
                      <TableCell>
                        <a href={doc.document_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-primary/80 hover:text-primary font-medium bg-primary/10 px-3 py-1.5 rounded-lg transition-colors group-hover:bg-primary/20">
                          عرض المستند <ExternalLink className="h-3 w-3" />
                        </a>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`${status.color} backdrop-blur-md flex w-fit items-center gap-1.5 px-2.5 py-1 rounded-lg border`}>
                          <StatusIcon className="h-3.5 w-3.5" />
                          <span className="font-bold text-xs tracking-wide">{status.label}</span>
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">
                        {new Date(doc.created_at).toLocaleDateString("ar-EG")}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}