// hooks/commerce/useProducts.ts
import { useInfiniteQuery } from "@tanstack/react-query";
import { CommerceService } from "@/services/commerce.service";
import { useAuthStore } from "@/store/auth-store";

export const useProducts = (storeId: number, limit: number = 20) => {
  const { isAuthenticated } = useAuthStore();

  return useInfiniteQuery({
    queryKey: ['commerce', 'products', storeId],
    queryFn: ({ pageParam = 0 }) =>
      CommerceService.getProducts(storeId, pageParam, limit),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.reduce((acc, page) => acc + page.data.length, 0);
      return totalFetched < lastPage.total ? totalFetched : undefined;
    },
    enabled: isAuthenticated && !!storeId,
    staleTime: 2 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
};