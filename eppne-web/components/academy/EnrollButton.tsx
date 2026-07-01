// components/academy/EnrollButton.tsx
"use client";

import { useSearchParams } from "next/navigation";
import { useEnrollMutation } from "@/hooks/academy-queries";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

interface EnrollButtonProps {
  courseId: number;
  isFree?: boolean;
  className?: string;
}

export function EnrollButton({ courseId, isFree = false, className = "" }: EnrollButtonProps) {
  const searchParams = useSearchParams();
  const affiliateCode = searchParams.get('ref') || searchParams.get('affiliate') || undefined;

  const enrollMutation = useEnrollMutation();

  const handleEnroll = () => {
    enrollMutation.mutate(
      {
        courseId,
        payload: {
          payment_method: isFree ? "FREE" : "WALLET",
          affiliate_code: affiliateCode,
        },
      },
      {
        onSuccess: () => {
          toast.success("تم التسجيل في الكورس بنجاح! 🎉");
        },
        onError: (error: any) => {
          toast.error(error.message || "فشل التسجيل في الكورس");
        },
      }
    );
  };

  return (
    <Button
      onClick={handleEnroll}
      disabled={enrollMutation.isPending}
      className={className}
    >
      {enrollMutation.isPending ? (
        <>
          <Loader2 className="ml-2 h-4 w-4 animate-spin" />
          جاري التسجيل...
        </>
      ) : (
        "سجل الآن"
      )}
    </Button>
  );
}