// app/(dashboard)/ai/approvals/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useAgentStore } from '@/store/agentStore';
import { useAuth } from '@/hooks/auth/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Loader2, CheckCircle, XCircle, Clock, FileText } from 'lucide-react';

export default function ApprovalsPage() {
  const { user } = useAuth();
  const { approvals, isLoading, fetchPendingApprovals, resolveApproval } = useAgentStore();
  const [feedback, setFeedback] = useState<Record<number, string>>({});
  const [processingId, setProcessingId] = useState<number | null>(null);

  useEffect(() => {
    fetchPendingApprovals();
    // تحديث كل 30 ثانية
    const interval = setInterval(fetchPendingApprovals, 30000);
    return () => clearInterval(interval);
  }, [fetchPendingApprovals]);

  const handleResolve = async (approvalId: number, status: 'APPROVED' | 'REJECTED') => {
    setProcessingId(approvalId);
    try {
      await resolveApproval(approvalId, {
        status,
        human_feedback: feedback[approvalId] || null,
      });
      toast.success(`تم ${status === 'APPROVED' ? 'الموافقة على' : 'رفض'} الإجراء`);
      setFeedback((prev) => {
        const newFeedback = { ...prev };
        delete newFeedback[approvalId];
        return newFeedback;
      });
    } catch (error: any) {
      toast.error(error.message || 'فشل حل الموافقة');
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="container mx-auto py-8 max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-primary/10 rounded-full">
          <Clock className="h-8 w-8 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">الموافقات البشرية</h1>
          <p className="text-muted-foreground text-sm">مراجعة إجراءات وكلاء الذكاء الاصطناعي التي تتطلب موافقتك</p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : approvals.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
            <p>لا توجد موافقات معلقة</p>
            <p className="text-sm">جميع إجراءات الوكلاء تمت معالجتها تلقائياً أو بواسطة مشرفين آخرين</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {approvals.map((approval) => (
            <Card key={approval.id} className="border-l-4 border-l-yellow-500">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-base">#{approval.id} - {approval.action_type}</CardTitle>
                    <CardDescription>
                      من الوكيل #{approval.agent_id} • {new Date(approval.created_at).toLocaleString('ar-EG')}
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-300">
                    في الانتظار
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-muted p-3 rounded-md">
                  <p className="text-sm font-medium mb-1 flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    البيانات المقترحة
                  </p>
                  <pre className="text-xs whitespace-pre-wrap bg-background p-2 rounded border">
                    {JSON.stringify(approval.proposed_payload, null, 2)}
                  </pre>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">ملاحظاتك (اختياري)</label>
                  <Textarea
                    placeholder="أضف تعليقاً لتوضيح سبب القرار..."
                    value={feedback[approval.id] || ''}
                    onChange={(e) => setFeedback({ ...feedback, [approval.id]: e.target.value })}
                    rows={2}
                  />
                </div>
              </CardContent>
              <CardFooter className="flex justify-end gap-2">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleResolve(approval.id, 'REJECTED')}
                  disabled={processingId === approval.id}
                >
                  {processingId === approval.id ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <XCircle className="h-4 w-4 mr-1" />}
                  رفض
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => handleResolve(approval.id, 'APPROVED')}
                  disabled={processingId === approval.id}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {processingId === approval.id ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <CheckCircle className="h-4 w-4 mr-1" />}
                  موافقة
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}