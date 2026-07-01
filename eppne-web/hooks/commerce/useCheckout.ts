// hooks/commerce/useCheckout.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CommerceService } from "@/services/commerce.service";
import { CheckoutRequest, CheckoutResponse } from "@/types/commerce";
import { useCartStore } from "@/store/cart-store";
import { toast } from "sonner";

// ✅ توليد Idempotency Key
const generateIdempotencyKey = (): string => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `IDEMP-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
};

export const useCheckout = () => {
  const queryClient = useQueryClient();
  const { clearCart } = useCartStore();

  return useMutation({
    mutationFn: async (payload: Omit<CheckoutRequest, 'idempotency_key'>) => {
      const fullPayload: CheckoutRequest = {
        ...payload,
        idempotency_key: generateIdempotencyKey(),
      };
      return CommerceService.checkout(fullPayload);
    },
    onSuccess: (data: CheckoutResponse) => {
      toast.success(`تم إتمام الطلب بنجاح! 🎉`, { duration: 4000 });
      clearCart();
      queryClient.invalidateQueries({ queryKey: ['commerce', 'orders'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل إتمام الشراء');
    },
  });
};