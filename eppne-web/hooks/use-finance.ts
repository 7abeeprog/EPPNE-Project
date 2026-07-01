// hooks/use-finance.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import { useFinanceStore } from "@/store/finance-store"; // سيقتصر دوره الآن على الواجهة فقط
import { toast } from "sonner";

export const useFinance = () => {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();

  // 🟢 1. جلب حالات الواجهة (UI & Web3) من Zustand فقط (لا علاقة له بالـ API بعد الآن)
  const { cryptoMode, setCryptoMode, isWeb3Loading } = useFinanceStore();

  // 🟢 2. جلب الأرصدة (Balances) مع درع الكاش السيادي
  const { 
    data: balances = null, 
    isLoading: isBalancesLoading, 
    error: balancesError,
    refetch: refetchBalances 
  } = useQuery({
    queryKey: ['finance', 'balances'],
    queryFn: async () => {
      const response = await apiClient.get('/finance/balances');
      return response.data;
    },
    enabled: !!isAuthenticated, // السحر هنا: لن يعمل إلا إذا كان القائد مسجلاً للدخول!
    staleTime: 1000 * 60 * 2, // كاش تكتيكي لمدة دقيقتين
  });

  // 🟢 3. جلب سجل العمليات (Transactions)
  const { 
    data: transactions = [], 
    isLoading: isTransactionsLoading, 
    error: transactionsError,
    refetch: refetchTransactions 
  } = useQuery({
    queryKey: ['finance', 'transactions'],
    queryFn: async () => {
      const response = await apiClient.get('/finance/transactions');
      return response.data;
    },
    enabled: !!isAuthenticated,
    staleTime: 1000 * 60 * 2,
  });

  // 🟢 4. محركات العمليات المالية (Mutations) مع تحديث فوري للكاش (Invalidation)
  const transferMutation = useMutation({
    mutationFn: async (payload: any) => await apiClient.post('/finance/transfer', payload),
    onSuccess: () => {
      toast.success("تم تشفير واعتماد التحويل بنجاح!");
      queryClient.invalidateQueries({ queryKey: ['finance'] }); // يحدّث الأرصدة والسجلات معاً فوراً
    },
    onError: () => toast.error("فشل التحويل. يرجى مراجعة الرصيد أو الشبكة.")
  });

  const swapMutation = useMutation({
    mutationFn: async (payload: any) => await apiClient.post('/finance/swap', payload),
    onSuccess: () => {
      toast.success("تمت عملية المبادلة (Swap) بنجاح!");
      queryClient.invalidateQueries({ queryKey: ['finance'] });
    },
    onError: () => toast.error("فشلت المبادلة. تأكد من السيولة المتاحة.")
  });

  const depositMutation = useMutation({
    mutationFn: async (payload: any) => await apiClient.post('/finance/deposit', payload),
    onSuccess: () => {
      toast.success("تم استلام إيداعك وجاري إضافته للمحفظة!");
      queryClient.invalidateQueries({ queryKey: ['finance'] });
    },
    onError: () => toast.error("فشلت عملية الإيداع.")
  });

  const withdrawMutation = useMutation({
    mutationFn: async (payload: any) => await apiClient.post('/finance/withdraw', payload),
    onSuccess: () => {
      toast.success("تم تشفير طلب السحب وإرساله للشبكة بنجاح!");
      queryClient.invalidateQueries({ queryKey: ['finance'] });
    },
    onError: () => toast.error("فشل طلب السحب. يرجى مراجعة الشروط والأرصدة.")
  });

  // تجميع حالات التحميل والأخطاء لسهولة الاستخدام في المكونات
  const isLoading = isBalancesLoading || isTransactionsLoading;
  const error = balancesError || transactionsError;

  return {
    // البيانات وحالات التحميل
    balances,
    transactions,
    isLoading,
    isWeb3Loading,
    error,
    cryptoMode,
    setCryptoMode,
    
    // دوال إعادة الجلب اليدوية
    refetchBalances,
    refetchTransactions,

    // العمليات (تم تصدير الـ mutateAsync لتعمل كـ Promise كما كان متوقعاً في الكود القديم)
    transfer: transferMutation.mutateAsync,
    swap: swapMutation.mutateAsync,
    deposit: depositMutation.mutateAsync,
    withdraw: withdrawMutation.mutateAsync,

    // 💡 تصدير المحركات بالكامل لمنح المكونات قدرة استخدام (depositMutation.isPending) في أزرار التحميل
    mutations: {
      transfer: transferMutation,
      swap: swapMutation,
      deposit: depositMutation,
      withdraw: withdrawMutation,
    }
  };
};