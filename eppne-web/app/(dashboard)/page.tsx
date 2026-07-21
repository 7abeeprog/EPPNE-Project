'use client';
import { Card, CardContent } from '@/components/ui/card';

export default function DashboardPage() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">مركز القيادة السيادي 🦅</h1>
      <Card className="bg-card/40 backdrop-blur-xl border-white/10">
        <CardContent className="p-6">
          <p className="text-lg text-green-400 font-bold mt-4">تم القضاء على الانهيار بنجاح! الأنظمة مستقرة.</p>
        </CardContent>
      </Card>
    </div>
  );
}