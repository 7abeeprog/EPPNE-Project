// app/(dashboard)/academy/certificates/[courseId]/page.tsx
"use client";

import { useRouter, useParams } from "next/navigation";
import { useMemo } from "react";

// ✅ استبدال المتجر القديم بالهوكات الجديدة
import { useCourse, useMyCertificates } from "@/hooks/academy-queries";
import { Certificate } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Download,
  Award,
  Share2,
  ArrowRight,
  ShieldAlert,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

export default function CertificateView() {
  const router = useRouter();
  const params = useParams();
  const courseId = Number(params.courseId);

  // ✅ 1. جلب بيانات الكورس
  const {
    data: course,
    isLoading: isCourseLoading,
    error: courseError,
  } = useCourse(courseId);

  // ✅ 2. جلب شهادات الطالب (مع Pagination)
  const {
    data: certificatesData,
    isLoading: isCertLoading,
    error: certError,
  } = useMyCertificates(0, 50);

  const certificates = certificatesData?.data || [];

  const isLoading = isCourseLoading || isCertLoading;

  // ✅ 3. البحث عن الشهادة الخاصة بهذا الكورس (useMemo)
  const certificate = useMemo(() => {
    return certificates.find((cert: Certificate) => cert.course_id === courseId);
  }, [certificates, courseId]);

  // ✅ 4. معالجة الأخطاء
  if (courseError) {
    const error = handleError(courseError, "جلب بيانات الكورس");
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
        <div className="max-w-lg w-full bg-destructive/10 border border-destructive/20 rounded-3xl p-10 text-center shadow-[0_0_40px_rgba(var(--destructive-rgb),0.2)]">
          <AlertCircle className="w-20 h-20 text-destructive mx-auto mb-6 animate-pulse" />
          <h2 className="text-3xl font-black text-foreground mb-4">فشل في تحميل البيانات</h2>
          <p className="text-muted-foreground text-lg mb-8">{error.message}</p>
          <Button
            onClick={() => router.push("/academy")}
            size="lg"
            className="rounded-xl h-14 px-8 text-lg font-bold shadow-lg"
          >
            العودة إلى الأكاديمية
          </Button>
        </div>
      </div>
    );
  }

  if (certError) {
    const error = handleError(certError, "جلب شهاداتك");
    // نعرض خطأ لكن نسمح بالمتابعة إذا كانت البيانات موجودة
    toast.error(error.message);
  }

  // ✅ 5. حالة التحميل
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 animate-in fade-in">
        <Loader2 className="h-12 w-12 text-primary animate-spin mb-6" />
        <Skeleton className="max-w-5xl w-full aspect-[1.414/1] rounded-none border-[10px] border-primary/10 bg-card/40" />
      </div>
    );
  }

  // ✅ 6. درع الحماية: منع الوصول إذا لم يتم اعتماد الشهادة
  if (!certificate) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 animate-in fade-in zoom-in-95">
        <div className="max-w-lg w-full bg-destructive/10 border border-destructive/20 rounded-3xl p-10 text-center shadow-[0_0_40px_rgba(var(--destructive-rgb),0.2)]">
          <ShieldAlert className="w-20 h-20 text-destructive mx-auto mb-6 animate-pulse" />
          <h2 className="text-3xl font-black text-foreground mb-4">الدخول مقيد (مستوى أمني)</h2>
          <p className="text-muted-foreground text-lg mb-8">
            لم يتم العثور على شهادة معتمدة لك في هذا المسار. يجب اجتياز كافة المهام والاختبارات
            للحصول على التوثيق السيادي.
          </p>
          <Button
            onClick={() => router.push(`/academy/classroom/${courseId}`)}
            size="lg"
            className="rounded-xl h-14 px-8 text-lg font-bold shadow-lg"
          >
            العودة لغرفة التعلم
          </Button>
        </div>
      </div>
    );
  }

  // ✅ 7. دالة الطباعة
  const handlePrint = () => {
    window.print();
  };

  // ✅ 8. دالة المشاركة
  const handleShare = async () => {
    try {
      await navigator.share({
        title: `شهادة إتمام - ${course?.title || "كورس"}`,
        text: `لقد حصلت على شهادة إتمام في ${course?.title || "كورس"} من منصة EPPNE!`,
        url: window.location.href,
      });
    } catch {
      // المستخدم ألغى المشاركة أو المتصفح لا يدعمها
      toast.info("يمكنك نسخ الرابط ومشاركته يدوياً.");
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative">
      {/* خلفية نيون زجاجية (تختفي عند الطباعة) */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10 print:hidden" />

      {/* شريط التحكم العلوي (يختفي عند الطباعة) */}
      <div className="max-w-5xl w-full flex flex-col sm:flex-row justify-between items-center gap-4 mb-8 print:hidden animate-in slide-in-from-top-4 duration-500">
        <Button
          variant="ghost"
          size="lg"
          onClick={() => router.back()}
          className="rounded-xl hover:bg-background/50 text-muted-foreground hover:text-foreground"
        >
          <ArrowRight className="ml-2 h-5 w-5" /> العودة لسجل الشهادات
        </Button>
        <div className="flex gap-4 w-full sm:w-auto">
          <Button
            variant="outline"
            size="lg"
            onClick={handleShare}
            className="rounded-xl flex-1 sm:flex-none border-primary/20 hover:bg-primary/10"
          >
            <Share2 className="ml-2 h-5 w-5" /> مشاركة التوثيق
          </Button>
          <Button
            size="lg"
            onClick={handlePrint}
            className="rounded-xl flex-1 sm:flex-none bg-primary text-primary-foreground shadow-[0_0_20px_rgba(var(--primary-rgb),0.4)] hover:scale-105 transition-all font-bold"
          >
            <Download className="ml-2 h-5 w-5" /> استخراج PDF
          </Button>
        </div>
      </div>

      {/* تصميم الشهادة (Certificate Layout - Print Ready) */}
      <Card
        className="w-full max-w-5xl aspect-[1.414/1] relative bg-card overflow-hidden border-[10px] border-double border-primary/30 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] flex flex-col items-center justify-center text-center p-8 md:p-16 print:shadow-none print:border-black animate-in zoom-in-95 duration-700"
        id="certificate"
      >
        {/* خلفيات وعلامات مائية */}
        <div className="absolute inset-0 bg-[url('/noise.png')] opacity-[0.03] mix-blend-overlay pointer-events-none" />
        <div className="absolute top-10 left-10 w-48 h-48 bg-primary/10 rounded-full blur-[80px] print:hidden" />
        <div className="absolute bottom-10 right-10 w-64 h-64 bg-emerald-500/10 rounded-full blur-[100px] print:hidden" />

        {/* إطارات الزوايا */}
        <div className="absolute top-8 left-8 h-16 w-16 border-t-4 border-l-4 border-primary/40 rounded-tl-2xl print:border-black" />
        <div className="absolute top-8 right-8 h-16 w-16 border-t-4 border-r-4 border-primary/40 rounded-tr-2xl print:border-black" />
        <div className="absolute bottom-8 left-8 h-16 w-16 border-b-4 border-l-4 border-primary/40 rounded-bl-2xl print:border-black" />
        <div className="absolute bottom-8 right-8 h-16 w-16 border-b-4 border-r-4 border-primary/40 rounded-br-2xl print:border-black" />

        <Award className="w-20 h-20 md:w-24 md:h-24 text-primary mb-6 relative z-10 print:text-black drop-shadow-md print:drop-shadow-none" />

        <h1 className="text-4xl md:text-5xl font-black text-foreground mb-4 relative z-10 tracking-widest uppercase print:text-black">
          شهادة إتمام سيادية
        </h1>
        <p className="text-lg md:text-xl text-muted-foreground mb-8 md:mb-12 relative z-10 print:text-gray-700">
          تشهد منصة EPPNE الأكاديمية بأن
        </p>

        <h2 className="text-3xl md:text-4xl font-bold text-primary mb-8 md:mb-12 relative z-10 border-b-2 border-primary/30 pb-4 px-12 inline-block print:text-black print:border-black">
          المجند / المتدرب رقم: #{certificate.user_id}
        </h2>

        <p className="text-lg md:text-xl text-muted-foreground mb-6 relative z-10 print:text-gray-700 max-w-3xl">
          قد أتم بنجاح وبكفاءة عالية كافة المتطلبات الأكاديمية والمشاريع التكتيكية الخاصة بمسار:
        </p>

        <h3 className="text-2xl md:text-3xl font-black text-foreground mb-4 relative z-10 print:text-black">
          {course?.title || "كورس غير معروف"}
        </h3>

        <p className="text-lg font-bold text-emerald-500 mb-12 md:mb-16 relative z-10 print:text-gray-800">
          بمعدل إنجاز واعتماد: {certificate.grade}%
        </p>

        <div className="flex justify-between w-full px-10 md:px-20 relative z-10 mt-auto items-end">
          <div className="text-center">
            <div className="border-b-2 border-foreground/50 print:border-black w-32 md:w-40 mb-2" />
            <p className="text-sm text-muted-foreground font-bold print:text-gray-800">
              تاريخ الإصدار
            </p>
            <p className="text-sm font-black mt-1 print:text-black">
              {new Date(certificate.issued_at).toLocaleDateString("ar-EG")}
            </p>
          </div>

          {/* ختم سيادي (Seal) */}
          <div className="relative flex items-center justify-center w-24 h-24 md:w-32 md:h-32 mb-4">
            <div className="absolute inset-0 border-4 border-dashed border-primary/40 rounded-full animate-[spin_20s_linear_infinite] print:animate-none print:border-gray-400" />
            <div className="absolute inset-2 border-2 border-primary/60 rounded-full print:border-gray-500" />
            <div className="text-center rotate-[-15deg]">
              <p className="text-[10px] md:text-xs font-black text-primary/80 uppercase tracking-widest print:text-gray-600">
                EPPNE
              </p>
              <p className="text-[10px] md:text-xs font-black text-primary/80 uppercase tracking-widest print:text-gray-600">
                VERIFIED
              </p>
            </div>
          </div>

          <div className="text-center">
            <div className="border-b-2 border-foreground/50 print:border-black w-32 md:w-40 mb-2" />
            <p className="text-sm text-muted-foreground font-bold print:text-gray-800">
              التوثيق المشفر (Hash)
            </p>
            <p
              className="text-xs font-mono font-bold mt-1 max-w-[120px] truncate print:text-black"
              title={certificate.certificate_hash}
            >
              {certificate.certificate_hash
                ? `${certificate.certificate_hash.substring(0, 10)}...`
                : "PENDING"}
            </p>
          </div>
        </div>
      </Card>

      {/* تنسيقات الطباعة */}
      <style
        dangerouslySetInnerHTML={{
          __html: `
            @media print {
              body * { visibility: hidden; }
              #certificate, #certificate * { visibility: visible; }
              #certificate {
                position: absolute;
                left: 0;
                top: 0;
                width: 100%;
                height: 100vh;
                box-shadow: none !important;
                margin: 0 !important;
                border: 10px solid #000 !important;
                border-radius: 0 !important;
              }
              .print\\:hidden { display: none !important; }
              .print\\:border-black { border-color: #000 !important; }
              .print\\:text-black { color: #000 !important; }
              .print\\:text-gray-700 { color: #4a4a4a !important; }
              .print\\:text-gray-800 { color: #2d2d2d !important; }
              .print\\:text-gray-600 { color: #4a4a4a !important; }
              .print\\:shadow-none { box-shadow: none !important; }
              .print\\:drop-shadow-none { filter: drop-shadow(none) !important; }
              .print\\:bg-white { background-color: #fff !important; }
              .print\\:animate-none { animation: none !important; }
            }
          `,
        }}
      />
    </div>
  );
}