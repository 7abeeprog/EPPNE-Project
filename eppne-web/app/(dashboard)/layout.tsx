// app/(dashboard)/layout.tsx
import { Sidebar } from "@/components/layout/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground selection:bg-primary/30">

      {/* 1. الشريط الجانبي السيادي */}
      <Sidebar />

      {/* 2. منطقة المحتوى (القطاعات المتغيرة) */}
      <main className="flex-1 overflow-x-hidden overflow-y-auto bg-grid-white/[0.02] relative">

        {/* إضاءات خلفية سيادية (جمالية) */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/10 rounded-full blur-[120px] -z-10 pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-blue-500/10 rounded-full blur-[120px] -z-10 pointer-events-none" />

        {/* محتوى الصفحة الحالية يظهر هنا */}
        <div className="p-4 md:p-6 lg:p-8 relative z-10 w-full min-h-full">
          {children}
        </div>

      </main>
    </div>
  );
}