// app/(dashboard)/finance/admin/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/identity/useAuth';
import { FinanceService } from '@/services/finance.service';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { Loader2, Coins, RefreshCw, Lock, Unlock, TrendingUp, Bot } from 'lucide-react';
import { useAgentStore } from '@/store/agentStore';

export default function AdminFinancePage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const { executeAgentAction } = useAgentStore();

  // حالة Crypto Mode
  const [cryptoMode, setCryptoMode] = useState<'FULL_CRYPTO' | 'POINTS_ONLY'>('FULL_CRYPTO');
  const [isCryptoModeLoading, setIsCryptoModeLoading] = useState(false);

  // حالة أسعار الصرف
  const [exchangeRates, setExchangeRates] = useState<Record<string, number>>({
    MR_USDT: 1,
    MR_POUND: 0.5,
    MR7: 2,
    NBT: 0.8,
    MRX: 1.2,
    LOYALTY_POINTS: 0.1,
  });
  const [tempRates, setTempRates] = useState<Record<string, string>>({});

  // حالة الحد الأقصى للطباعة
  const [maxSupply, setMaxSupply] = useState<Record<string, number>>({
    MR_USDT: 1000000,
    MR_POUND: 500000,
    MR7: 200000,
    NBT: 300000,
    MRX: 400000,
    LOYALTY_POINTS: 10000000,
  });
  const [tempMaxSupply, setTempMaxSupply] = useState<Record<string, string>>({});

  // حالة طباعة العملات
  const [mintCurrency, setMintCurrency] = useState('MR_USDT');
  const [mintAmount, setMintAmount] = useState('');

  // التحقق من صلاحيات المشرف
  useEffect(() => {
    if (!authLoading && user) {
      const isAdmin = user.system_role === 'SUPER_ADMIN' || user.system_role === 'ADMIN';
      if (!isAdmin) {
        toast.error('هذه الصفحة مخصصة للمشرفين فقط');
        router.push('/dashboard');
      }
    }
  }, [user, authLoading, router]);

  // جلب وضع العملات الحالي
  useEffect(() => {
    const fetchCryptoMode = async () => {
      try {
        const data = await FinanceService.getCryptoMode();
        setCryptoMode(data.crypto_mode as 'FULL_CRYPTO' | 'POINTS_ONLY');
      } catch (error) {
        console.error('Failed to fetch crypto mode:', error);
      }
    };
    fetchCryptoMode();
  }, []);

  // ==========================================
  // 1. تحديث وضع العملات
  // ==========================================
  const handleToggleCryptoMode = async (checked: boolean) => {
    const mode = checked ? 'FULL_CRYPTO' : 'POINTS_ONLY';
    setIsCryptoModeLoading(true);
    try {
      await FinanceService.setCryptoMode(mode);
      setCryptoMode(mode);
      toast.success(`تم تغيير وضع العملات إلى ${mode === 'FULL_CRYPTO' ? 'عملات رقمية كاملة' : 'نقاط فقط'}`);
    } catch (error: any) {
      toast.error(error.message || 'فشل في تحديث وضع العملات');
    } finally {
      setIsCryptoModeLoading(false);
    }
  };

  // ==========================================
  // 2. تحديث أسعار الصرف
  // ==========================================
  const handleExchangeRateChange = (currency: string, value: string) => {
    setTempRates((prev) => ({ ...prev, [currency]: value }));
  };

  const handleSubmitExchangeRates = async () => {
    setIsLoading(true);
    try {
      // تحويل القيم المدخلة إلى أرقام
      const updatedRates: Record<string, number> = {};
      for (const [currency, rateStr] of Object.entries(tempRates)) {
        if (rateStr) {
          const rate = parseFloat(rateStr);
          if (isNaN(rate) || rate <= 0) {
            toast.error(`سعر صرف غير صحيح للعملة ${currency}`);
            return;
          }
          updatedRates[currency] = rate;
        }
      }

      if (Object.keys(updatedRates).length === 0) {
        toast.error('يرجى إدخال أسعار صرف جديدة');
        return;
      }

      await FinanceService.setExchangeRates(updatedRates);
      
      // تحديث الحالة المحلية
      setExchangeRates((prev) => ({ ...prev, ...updatedRates }));
      setTempRates({});
      toast.success('تم تحديث أسعار الصرف بنجاح');
    } catch (error: any) {
      toast.error(error.message || 'فشل في تحديث أسعار الصرف');
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================
  // 3. تحديث الحد الأقصى للطباعة
  // ==========================================
  const handleMaxSupplyChange = (currency: string, value: string) => {
    setTempMaxSupply((prev) => ({ ...prev, [currency]: value }));
  };

  const handleSubmitMaxSupply = async () => {
    setIsLoading(true);
    try {
      const updatedSupply: Record<string, number> = {};
      for (const [currency, supplyStr] of Object.entries(tempMaxSupply)) {
        if (supplyStr) {
          const supply = parseFloat(supplyStr);
          if (isNaN(supply) || supply < 0) {
            toast.error(`قيمة غير صحيحة للعملة ${currency}`);
            return;
          }
          updatedSupply[currency] = supply;
        }
      }

      if (Object.keys(updatedSupply).length === 0) {
        toast.error('يرجى إدخال حدود قصوى جديدة');
        return;
      }

      await FinanceService.setMaxSupply(updatedSupply);
      
      // تحديث الحالة المحلية
      setMaxSupply((prev) => ({ ...prev, ...updatedSupply }));
      setTempMaxSupply({});
      toast.success('تم تحديث الحد الأقصى للطباعة بنجاح');
    } catch (error: any) {
      toast.error(error.message || 'فشل في تحديث الحد الأقصى للطباعة');
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================
  // 4. طباعة عملات جديدة
  // ==========================================
  const handleMint = async () => {
    if (!mintAmount || parseFloat(mintAmount) <= 0) {
      toast.error('يرجى إدخال مبلغ صحيح أكبر من الصفر');
      return;
    }

    setIsLoading(true);
    try {
      await FinanceService.mintCurrency({
        currency: mintCurrency,
        amount: parseFloat(mintAmount),
      });
      toast.success(`تم طباعة ${mintAmount} من ${mintCurrency} بنجاح`);
      setMintAmount('');
    } catch (error: any) {
      toast.error(error.message || 'فشل في طباعة العملات');
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================
  // 5. توصيات الذكاء الاصطناعي
  // ==========================================
  const handleAIRecommendation = async () => {
    try {
      const result = await executeAgentAction(1, 'ANALYZE_FINANCE', {
        task: 'تقديم توصيات لتحسين الاستقرار المالي',
        current_mode: cryptoMode,
        exchange_rates: exchangeRates,
      });
      toast.info('تم تحليل الوضع المالي، اطلع على التوصيات');
      console.log('AI Recommendations:', result);
    } catch (error) {
      toast.error('فشل تحليل الوضع المالي');
    }
  };

  // عرض التحميل أثناء جلب بيانات المستخدم
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // التحقق من الصلاحيات
  const isAdmin = user?.system_role === 'SUPER_ADMIN' || user?.system_role === 'ADMIN';
  if (!isAdmin) {
    return null; // أو صفحة "غير مصرح"
  }

  return (
    <div className="container mx-auto py-8 max-w-5xl">
      <div className="flex items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-full">
            <Coins className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">لوحة تحكم النظام المالي</h1>
            <p className="text-muted-foreground text-sm">إدارة العملات، أسعار الصرف، والطباعة</p>
          </div>
        </div>
        <Button variant="outline" onClick={handleAIRecommendation}>
          <Bot className="mr-2 h-4 w-4" />
          توصيات الذكاء الاصطناعي
        </Button>
      </div>

      <Tabs defaultValue="crypto-mode" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="crypto-mode">وضع العملات</TabsTrigger>
          <TabsTrigger value="exchange-rates">أسعار الصرف</TabsTrigger>
          <TabsTrigger value="max-supply">الحد الأقصى للطباعة</TabsTrigger>
          <TabsTrigger value="mint">طباعة العملات</TabsTrigger>
        </TabsList>

        {/* ============================================ */}
        {/* علامة تبويب: وضع العملات */}
        {/* ============================================ */}
        <TabsContent value="crypto-mode">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {cryptoMode === 'FULL_CRYPTO' ? <Unlock className="h-5 w-5 text-green-500" /> : <Lock className="h-5 w-5 text-red-500" />}
                وضع العملات الحالي: <span className="font-bold">{cryptoMode === 'FULL_CRYPTO' ? '💎 عملات رقمية كاملة' : '⭐ نقاط فقط'}</span>
              </CardTitle>
              <CardDescription>
                {cryptoMode === 'FULL_CRYPTO' 
                  ? 'النظام يدعم جميع العملات الرقمية (MR_USDT, MR_POUND, MR7, NBT, MRX, LOYALTY_POINTS) مع إمكانية التحويل والصرافة.'
                  : 'النظام يعمل بنظام النقاط فقط (LOYALTY_POINTS)، ويتم تعطيل جميع العملات الأخرى.'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                <div>
                  <p className="font-medium">تفعيل العملات الرقمية الكاملة</p>
                  <p className="text-sm text-muted-foreground">
                    {cryptoMode === 'FULL_CRYPTO' ? 'جميع العملات مفعلة' : 'يتم التعامل بالنقاط فقط'}
                  </p>
                </div>
                <Switch
                  checked={cryptoMode === 'FULL_CRYPTO'}
                  onCheckedChange={handleToggleCryptoMode}
                  disabled={isCryptoModeLoading}
                />
              </div>
            </CardContent>
            <CardFooter className="text-xs text-muted-foreground border-t pt-4">
              ⚠️ تغيير هذا الإعداد يؤثر على جميع عمليات الدفع والتحويل في النظام.
            </CardFooter>
          </Card>
        </TabsContent>

        {/* ============================================ */}
        {/* علامة تبويب: أسعار الصرف */}
        {/* ============================================ */}
        <TabsContent value="exchange-rates">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                أسعار الصرف
              </CardTitle>
              <CardDescription>
                قم بتحديث أسعار الصرف بين العملات المختلفة (بالنسبة إلى MR_USDT كمرجع)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(exchangeRates).map(([currency, rate]) => (
                  <div key={currency} className="flex items-center gap-2">
                    <Label htmlFor={`rate-${currency}`} className="w-28 font-medium">
                      {currency}
                    </Label>
                    <Input
                      id={`rate-${currency}`}
                      type="number"
                      step="0.01"
                      min="0.01"
                      placeholder={rate.toString()}
                      value={tempRates[currency] || ''}
                      onChange={(e) => handleExchangeRateChange(currency, e.target.value)}
                      className="flex-1"
                    />
                    <span className="text-sm text-muted-foreground w-12">MR_USDT</span>
                  </div>
                ))}
              </div>
            </CardContent>
            <CardFooter className="flex justify-between border-t pt-4">
              <p className="text-xs text-muted-foreground">
                القيم الحالية معروضة كمرجع، أدخل القيم الجديدة لتحديثها.
              </p>
              <Button onClick={handleSubmitExchangeRates} disabled={isLoading || Object.keys(tempRates).length === 0}>
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                تحديث الأسعار
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* ============================================ */}
        {/* علامة تبويب: الحد الأقصى للطباعة */}
        {/* ============================================ */}
        <TabsContent value="max-supply">
          <Card>
            <CardHeader>
              <CardTitle>الحد الأقصى للطباعة</CardTitle>
              <CardDescription>
                تحديد الحد الأعلى الذي يمكن طباعته من كل عملة
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(maxSupply).map(([currency, supply]) => (
                  <div key={currency} className="flex items-center gap-2">
                    <Label htmlFor={`supply-${currency}`} className="w-28 font-medium">
                      {currency}
                    </Label>
                    <Input
                      id={`supply-${currency}`}
                      type="number"
                      step="1"
                      min="0"
                      placeholder={supply.toString()}
                      value={tempMaxSupply[currency] || ''}
                      onChange={(e) => handleMaxSupplyChange(currency, e.target.value)}
                      className="flex-1"
                    />
                  </div>
                ))}
              </div>
            </CardContent>
            <CardFooter className="flex justify-between border-t pt-4">
              <p className="text-xs text-muted-foreground">
                القيم الحالية معروضة كمرجع، أدخل القيم الجديدة لتحديثها.
              </p>
              <Button onClick={handleSubmitMaxSupply} disabled={isLoading || Object.keys(tempMaxSupply).length === 0}>
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                تحديث الحدود
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* ============================================ */}
        {/* علامة تبويب: طباعة العملات */}
        {/* ============================================ */}
        <TabsContent value="mint">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Coins className="h-5 w-5 text-yellow-500" />
                طباعة عملات جديدة
              </CardTitle>
              <CardDescription>
                طباعة عملات جديدة (يتطلب صلاحيات البنك المركزي)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="mint-currency">العملة</Label>
                  <select
                    id="mint-currency"
                    value={mintCurrency}
                    onChange={(e) => setMintCurrency(e.target.value)}
                    className="w-full p-2 border rounded-md bg-background"
                  >
                    <option value="MR_USDT">MR_USDT</option>
                    <option value="MR_POUND">MR_POUND</option>
                    <option value="MR7">MR7</option>
                    <option value="NBT">NBT</option>
                    <option value="MRX">MRX</option>
                    <option value="LOYALTY_POINTS">LOYALTY_POINTS</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="mint-amount">المبلغ</Label>
                  <Input
                    id="mint-amount"
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="أدخل المبلغ المراد طباعته"
                    value={mintAmount}
                    onChange={(e) => setMintAmount(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex justify-between border-t pt-4">
              <p className="text-xs text-muted-foreground text-red-500">
                ⚠️ هذه العملية غير قابلة للتراجع. تأكد من مراجعة الحد الأقصى للطباعة أولاً.
              </p>
              <Button onClick={handleMint} disabled={isLoading || !mintAmount} className="bg-yellow-600 hover:bg-yellow-700 text-white">
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Coins className="mr-2 h-4 w-4" />}
                طباعة العملات
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}