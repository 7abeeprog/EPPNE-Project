import { Sidebar } from "@/components/layout/sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    // 🟢 الحاوية الرئيسية: مرنة، تملأ الشاشة، وتدعم اللغة العربية RTL
    <div className="flex h-screen w-full overflow-hidden bg-background" dir="rtl">
      
      {/* 🟢 الشريط الجانبي السيادي */}
      <Sidebar />

      {/* 🟢 منطقة المحتوى: flex-1 تجعلها تتمدد لتملأ كل الفراغ المتبقي */}
      <main className="flex-1 w-full h-full overflow-y-auto overflow-x-hidden relative scroll-smooth custom-scrollbar">
        {/* يمكننا إضافة شريط علوي (Header) هنا لاحقاً */}
        <div className="w-full h-full">
          {children}
        </div>
      </main>
      
    </div>
  );
}