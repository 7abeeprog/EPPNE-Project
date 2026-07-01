// hooks/finance/useSwap.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FinanceService } from "@/services/finance.service";
import { SwapRequest } from "@/types/finance";
import { toast } from "sonner";

export const useSwap = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SwapRequest) => FinanceService.swap(payload),
    onSuccess: (data) => {
      toast.success(
        `تم صرافة ${data.from_amount} ${data.from_currency} إلى ${data.to_amount} ${data.to_currency} بنجاح! 💱`,
        { duration: 3000 }
      );
      queryClient.invalidateQueries({ queryKey: ['finance', 'wallet'] });
      queryClient.invalidateQueries({ queryKey: ['finance', 'history'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل إجراء الصرافة');
    },
  });
};