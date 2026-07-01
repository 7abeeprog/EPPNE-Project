// hooks/finance/useWallet.ts
import { useQuery } from "@tanstack/react-query";
import { FinanceService } from "@/services/finance.service";
import { useAuthStore } from "@/store/auth-store";

export const useWallet = () => {
  const { isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: ['finance', 'wallet'],
    queryFn: () => FinanceService.getWallet(),
    enabled: isAuthenticated,
    staleTime: 30 * 1000, // 30 ثانية
    refetchOnWindowFocus: true,
  });
};