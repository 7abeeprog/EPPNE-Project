// components/academy/TenantProvider.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AcademyService } from "@/services/academy.service";
import { useAuthStore } from "@/store/auth-store";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, ShieldAlert, PlusCircle, LayoutGrid } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  const [isOpen, setIsOpen] = useState(false);
  const [academyName, setAcademyName] = useState("");
  const [safeDomain, setSafeDomain] = useState("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const hostname = window.location.hostname;
      setSafeDomain(hostname === "localhost" ? "localhost.com" : hostname);
    }
  }, []);

  // ✅ استخدام AcademyService.getTenantByDomain
  const {
    data: tenant,
    isLoading: isTenantLoading,
    error,
  } = useQuery({
    queryKey: ["academy", "tenant", safeDomain],
    queryFn: () => AcademyService.getTenantByDomain(safeDomain),
    enabled: !!safeDomain,
    retry: false,
    staleTime: 10 * 60 * 1000,
  });

  // ✅ استخدام AcademyService.createTenant
  const createTenantMutation = useMutation({
    mutationFn: (payload: any) => AcademyService.createTenant(payload),
    onSuccess: () => {
      toast.success("تم تأسيس أكاديميتك بنجاح! جاري تهيئة القنوات السيادية...");
      setIsOpen(false);
      queryClient.invalidateQueries({ queryKey: ["academy", "tenant"] });
      router.refresh();
    },
    onError: (err: any) => {
      console.warn("تفاصيل الرفض من الباك إند:", err.response?.data);
      const detail = err.response?.data?.detail;
      let errorMsg = "فشل تأسيس الأكاديمية. تأكد من إعدادات الباك إند.";

      if (typeof detail === "string") {
        errorMsg = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        const fieldName = detail[0].loc[detail[0].loc.length - 1];
        errorMsg = `خطأ في الحقل [${fieldName}]: ${detail[0].msg}`;
      }

      toast.error(errorMsg);
    },
  });

  const handleCreateAcademy = (e: React.FormEvent) => {
    e.preventDefault();
    if (!academyName.trim()) return;

    if (!user) {
      toast.error("الدخول مقيد: يجب تسجيل الدخول أولاً لتأسيس كيان سيادي.");
      return;
    }

    createTenantMutation.mutate({
      name: academyName,
      domain: safeDomain,
      admin_id: user.id,
      branding: {
        primaryColor: "#00ffcc",
        logoUrl: "",
      },
    });
  };

  // 1️⃣ شاشة التحميل
  if (isTenantLoading || !safeDomain) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background relative">
        <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-primary/10 blur-[100px] rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
        <Loader2 className="animate-spin h-12 w-12 text-primary mb-4 relative z-10" />
        <p className="text-primary font-bold tracking-widest animate-pulse relative z-10">
          جاري التحقق من الهوية السيادية للكيان...
        </p>
      </div>
    );
  }

  // 2️⃣ لا يوجد Tenant
  if (error || !tenant) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4 text-center relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 w-[500px] h-[500px] bg-primary/10 blur-[150px] rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none" />

        <div className="p-5 bg-primary/5 border border-primary/20 rounded-full mb-6 shadow-[0_0_30px_rgba(var(--primary-rgb),0.2)]">
          <ShieldAlert className="h-16 w-16 text-primary opacity-90 animate-pulse" />
        </div>

        <h1 className="text-3xl md:text-5xl font-black mb-4 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary">
          منصة EPPNE الأكاديمية
        </h1>
        <p className="text-muted-foreground text-lg max-w-md mb-10 font-medium">
          هذا النطاق (<span className="font-bold text-foreground">{safeDomain}</span>) لا يمتلك أكاديمية مفعلة في قاعدة البيانات حتى الآن.
        </p>

        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogTrigger asChild>
            <Button
              size="lg"
              className="h-14 px-8 font-black text-lg shadow-[0_0_30px_rgba(var(--primary-rgb),0.4)] hover:shadow-[0_0_40px_rgba(var(--primary-rgb),0.6)] hover:scale-105 transition-all rounded-2xl"
            >
              <PlusCircle className="ml-2 h-6 w-6" /> أنشئ أكاديميتي الآن
            </Button>
          </DialogTrigger>

          <DialogContent className="sm:max-w-[450px] backdrop-blur-3xl bg-card/80 border border-primary/20 shadow-[0_0_60px_-15px_rgba(var(--primary-rgb),0.4)] rounded-[2rem]">
            <DialogHeader className="mb-4">
              <DialogTitle className="text-2xl font-black flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-xl border border-primary/20">
                  <LayoutGrid className="h-6 w-6 text-primary" />
                </div>
                تأسيس كيان أكاديمي
              </DialogTitle>
              <DialogDescription className="text-md mt-2 font-medium">
                أدخل اسم صرحك التعليمي لربطه بنطاقك المحلي الحالي شرعياً.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleCreateAcademy} className="space-y-6">
              <div className="space-y-3">
                <Label htmlFor="name" className="text-right block font-bold text-foreground text-lg">
                  اسم الأكاديمية / الجامعة
                </Label>
                <Input
                  id="name"
                  placeholder="مثال: جامعة EPPNE التكنولوجية"
                  value={academyName}
                  onChange={(e) => setAcademyName(e.target.value)}
                  className="h-14 bg-background/50 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary/50 text-lg rounded-xl shadow-inner transition-colors"
                  required
                />
              </div>

              <div className="space-y-3">
                <Label className="text-right block font-bold text-muted-foreground">النطاق المرتبط (تلقائي)</Label>
                <div className="h-14 flex items-center px-4 bg-black/20 text-muted-foreground font-mono rounded-xl border border-white/5 cursor-not-allowed">
                  {safeDomain}
                </div>
              </div>

              <Button
                type="submit"
                className="w-full h-14 text-lg font-black rounded-xl shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-transform mt-4"
                disabled={createTenantMutation.isPending}
              >
                {createTenantMutation.isPending ? (
                  <>
                    <Loader2 className="animate-spin ml-2 h-6 w-6" /> جاري البناء والتشجير...
                  </>
                ) : (
                  "إطلاق وتفعيل المنظومة الأكاديمية"
                )}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // 3️⃣ Tenant موجود
  return <>{children}</>;
}