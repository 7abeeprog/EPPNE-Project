"use client";

import { useAuthStore } from "@/store/auth-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export default function DashboardPage() {
  const { user } = useAuthStore();

  const { data: balances } = useQuery({
    queryKey: ["balances"],
    queryFn: async () => {
      const res = await apiClient.get("/finance/balances");
      return res.data.balances;
    },
    enabled: !!user,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">مرحباً {user?.name_ar || user?.username}</h1>
        <p className="text-muted-foreground">
          رتبتك السيادية: {user?.sovereign_rank}
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>رصيد المحفظة</CardTitle>
          </CardHeader>
          <CardContent>
            {balances ? (
              <ul className="space-y-2">
                {Object.entries(balances as Record<string, number>).map(([currency, amount]) => (
                  <li key={currency} className="flex justify-between">
                    <span>{currency}</span>
                    <span className="font-mono">{amount.toLocaleString()}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>جاري التحميل...</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>نقاط السمعة</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{user?.reputation_score || 100}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>حالة KYC</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-lg font-semibold ${
              user?.kyc_status === "VERIFIED" ? "text-green-600" : "text-yellow-600"
            }`}>
              {user?.kyc_status === "VERIFIED" ? "موثق" : "غير موثق"}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}