"use client";

import { BalanceCard } from "@/components/finance/balance-card";
import { Web3DepositWithdraw } from "@/components/finance/web3-deposit-withdraw";
import { AdminMintCard } from "@/components/finance/admin-mint-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowRightLeft, ShieldAlert, Wallet as WalletIcon } from "lucide-react";

export default function WalletPage() {
  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-10">
      {/* الترويسة */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">الخزينة المركزية</h1>
        <p className="text-muted-foreground mt-2">
          إدارة أرصدتك السيادية، النقاط، وعمليات الإيداع والسحب.
        </p>
      </div>

      <BalanceCard />

      {/* تبويبات التحكم */}
      <Tabs defaultValue="web3" className="w-full mt-8">
        <TabsList className="grid w-full grid-cols-3 lg:w-[600px]">
          <TabsTrigger value="web3" className="flex gap-2">
            <WalletIcon className="h-4 w-4" /> الخزينة (Web3)
          </TabsTrigger>
          <TabsTrigger value="transfer" className="flex gap-2">
            <ArrowRightLeft className="h-4 w-4" /> التحويل الداخلي
          </TabsTrigger>
          <TabsTrigger value="admin" className="flex gap-2 text-amber-600 data-[state=active]:text-amber-700">
            <ShieldAlert className="h-4 w-4" /> البنك المركزي
          </TabsTrigger>
        </TabsList>

        <div className="mt-6">
          <TabsContent value="web3" className="space-y-4 animate-in fade-in-50">
            <Web3DepositWithdraw />
          </TabsContent>

          <TabsContent value="transfer" className="space-y-4 animate-in fade-in-50">
            <div className="p-12 text-center border-2 border-dashed rounded-lg text-muted-foreground bg-muted/10">
              <ArrowRightLeft className="h-10 w-10 mx-auto opacity-20 mb-4" />
              <p className="text-lg font-medium">واجهة التحويل الداخلي بين الكيانات</p>
              <p className="text-sm">سيتم تفعيل هذه الخاصية قريباً</p>
            </div>
          </TabsContent>

          <TabsContent value="admin" className="space-y-4 animate-in fade-in-50">
             <AdminMintCard />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}