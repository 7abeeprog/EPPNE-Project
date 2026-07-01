// hooks/finance/useTransactionHistory.ts
import { useInfiniteQuery } from "@tanstack/react-query";
import { FinanceService } from "@/services/finance.service";
import { useAuthStore } from "@/store/auth-store";

export const useTransactionHistory = (limit: number = 20) => {
  const { isAuthenticated } = useAuthStore();

  return useInfiniteQuery({
    queryKey: ['finance', 'history', 'infinite'],
    queryFn: ({ pageParam = 0 }) =>
      FinanceService.getTransactionHistory(pageParam, limit),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.reduce((acc, page) => acc + page.data.length, 0);
      return totalFetched < lastPage.total ? totalFetched : undefined;
    },
    enabled: isAuthenticated,
    staleTime: 30 * 1000,
    // ✅ تقليل استهلاك موارد السيرفر
    refetchOnWindowFocus: false,
    refetchOnMount: true,
  });
};