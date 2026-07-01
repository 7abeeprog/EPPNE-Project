// hooks/finance/useTransfer.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FinanceService } from "@/services/finance.service";
import { TransferRequest, TransferResponse } from "@/types/finance";
import { toast } from "sonner";

// ✅ توليد Idempotency Key باستخدام crypto.randomUUID()
const generateIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback لبيئة التطوير
  return `IDEMP-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
};

export const useTransfer = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: Omit<TransferRequest, 'idempotency_key'>) => {
      // ✅ توليد idempotency_key داخل الهوك
      const fullPayload: TransferRequest = {
        ...payload,
        idempotency_key: generateIdempotencyKey(),
      };
      return FinanceService.transfer(fullPayload);
    },
    onSuccess: (data: TransferResponse) => {
      toast.success(`تم تحويل ${data.amount} ${data.currency} بنجاح! 🚀`, {
        duration: 3000,
      });
      // تحديث الرصيد والتاريخ
      queryClient.invalidateQueries({ queryKey: ['finance', 'wallet'] });
      queryClient.invalidateQueries({ queryKey: ['finance', 'history'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل إجراء التحويل');
    },
  });
};