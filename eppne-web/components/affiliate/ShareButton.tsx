// components/affiliate/ShareButton.tsx
"use client";

import { useState } from "react";
import { useAffiliateProfile } from "@/hooks/affiliate/useAffiliate";
import { Button } from "@/components/ui/button";
import { Share2, Link2, Copy, Check } from "lucide-react";
import { toast } from "sonner";

interface ShareButtonProps {
  productId?: number;
  courseId?: number;
  target: string;
  label?: string;
}

export function ShareButton({ productId, courseId, target, label = "شارك هذا المنتج" }: ShareButtonProps) {
  const { data: profile } = useAffiliateProfile();
  const [copied, setCopied] = useState(false);

  const generateShareLink = () => {
    const baseUrl = window.location.origin;
    const params = new URLSearchParams();
    params.set('ref', profile?.referral_code || '');
    if (productId) params.set('product', productId.toString());
    if (courseId) params.set('course', courseId.toString());
    return `${baseUrl}${target}?${params.toString()}`;
  };

  const handleShare = async () => {
    const shareUrl = generateShareLink();
    const shareText = `انضم إلى EPPNE واستفد من الخدمات السيادية! 🚀`;

    if (navigator.share) {
      try {
        await navigator.share({
          title: 'EPPNE - المنصة السيادية',
          text: shareText,
          url: shareUrl,
        });
        return;
      } catch (error) {
        // المستخدم ألغى المشاركة
        if ((error as Error).name !== 'AbortError') {
          toast.error('فشل المشاركة');
        }
        return;
      }
    }

    // نسخ الرابط
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success('تم نسخ رابط الدعوة!');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('فشل نسخ الرابط');
    }
  };

  return (
    <Button
      variant="outline"
      onClick={handleShare}
      className="rounded-xl border-amber-500/30 text-amber-500 hover:bg-amber-500 hover:text-white transition-all font-bold"
    >
      {copied ? (
        <Check className="ml-2 h-4 w-4" />
      ) : (
        <Share2 className="ml-2 h-4 w-4" />
      )}
      {copied ? 'تم النسخ!' : label}
    </Button>
  );
}