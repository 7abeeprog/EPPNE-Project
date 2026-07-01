// hooks/affiliate/useAffiliate.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AffiliateService } from "@/services/affiliate.service";
import { toast } from "sonner";

// ==========================================
// 1. ملف الداعي
// ==========================================
export const useAffiliateProfile = () => {
  return useQuery({
    queryKey: ['affiliate', 'profile'],
    queryFn: () => AffiliateService.getProfile(),
    staleTime: 5 * 60 * 1000,
  });
};

export const useUpdateAffiliateProfile = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: any) => AffiliateService.updateProfile(payload),
    onSuccess: () => {
      toast.success('تم تحديث ملف الداعي بنجاح');
      queryClient.invalidateQueries({ queryKey: ['affiliate', 'profile'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل تحديث ملف الداعي');
    },
  });
};

// ==========================================
// 2. روابط الدعوة
// ==========================================
export const useAffiliateLinks = (skip: number = 0, limit: number = 20) => {
  return useQuery({
    queryKey: ['affiliate', 'links', skip, limit],
    queryFn: () => AffiliateService.getLinks(skip, limit),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateAffiliateLink = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: any) => AffiliateService.createLink(payload),
    onSuccess: () => {
      toast.success('تم إنشاء رابط الدعوة بنجاح');
      queryClient.invalidateQueries({ queryKey: ['affiliate', 'links'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل إنشاء رابط الدعوة');
    },
  });
};

// ==========================================
// 3. العمولات
// ==========================================
export const useCommissions = (skip: number = 0, limit: number = 20, status?: string) => {
  return useQuery({
    queryKey: ['affiliate', 'commissions', skip, limit, status],
    queryFn: () => AffiliateService.getCommissions(skip, limit, status),
    staleTime: 1 * 60 * 1000,
  });
};

export const useReleaseCommissions = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => AffiliateService.releaseCommissions(),
    onSuccess: () => {
      toast.success('تم بدء عملية إفراج العمولات');
      queryClient.invalidateQueries({ queryKey: ['affiliate', 'commissions'] });
      queryClient.invalidateQueries({ queryKey: ['affiliate', 'stats'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل إفراج العمولات');
    },
  });
};

// ==========================================
// 4. سحب العمولات
// ==========================================
export const useWithdraw = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { amount: number }) => AffiliateService.withdraw(payload),
    onSuccess: () => {
      toast.success('تم سحب العمولات بنجاح');
      queryClient.invalidateQueries({ queryKey: ['affiliate', 'commissions'] });
      queryClient.invalidateQueries({ queryKey: ['affiliate', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['affiliate', 'profile'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل سحب العمولات');
    },
  });
};

// ==========================================
// 5. الإحصائيات
// ==========================================
export const useAffiliateStats = () => {
  return useQuery({
    queryKey: ['affiliate', 'stats'],
    queryFn: () => AffiliateService.getStats(),
    staleTime: 2 * 60 * 1000,
  });
};

export const useAffiliateDashboard = () => {
  return useQuery({
    queryKey: ['affiliate', 'dashboard'],
    queryFn: () => AffiliateService.getDashboardStats(),
    staleTime: 1 * 60 * 1000,
  });
};

// ==========================================
// 6. شجرة الإحالة
// ==========================================
export const useAffiliateTree = (maxDepth: number = 5) => {
  return useQuery({
    queryKey: ['affiliate', 'tree', maxDepth],
    queryFn: () => AffiliateService.getTree(maxDepth),
    staleTime: 5 * 60 * 1000,
  });
};