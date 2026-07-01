// hooks/saas/useInvoices.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SaaSService } from "@/services/saas.service";
import { CreateInvoiceRequest } from "@/types/saas";
import { toast } from "sonner";

export const useInvoices = (skip: number = 0, limit: number = 20) => {
  return useQuery({
    queryKey: ['saas', 'invoices', skip, limit],
    queryFn: () => SaaSService.getInvoices(skip, limit),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateInvoice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateInvoiceRequest) => SaaSService.createInvoice(payload),
    onSuccess: () => {
      toast.success('تم إنشاء الفاتورة بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'invoices'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل إنشاء الفاتورة');
    },
  });
};

export const usePayInvoice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (invoiceId: number) => SaaSService.payInvoice(invoiceId),
    onSuccess: () => {
      toast.success('تم دفع الفاتورة بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'invoices'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل دفع الفاتورة');
    },
  });
};

export const useCancelInvoice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (invoiceId: number) => SaaSService.cancelInvoice(invoiceId),
    onSuccess: () => {
      toast.success('تم إلغاء الفاتورة بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'invoices'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل إلغاء الفاتورة');
    },
  });
};