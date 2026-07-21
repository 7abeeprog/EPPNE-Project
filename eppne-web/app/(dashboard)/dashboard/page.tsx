// app/(dashboard)/dashboard/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { useNotificationStore } from '@/store/notificationStore';
import { useFinanceStore } from '@/store/finance-store';
import { useHealthStore } from '@/store/healthStore';
import { useAgentStore } from '@/store/agentStore';
import { useDigitalTwinStore } from '@/store/digitalTwinStore';
import { useAcademyUIStore as useAcademyStore } from '@/store/academy-ui-store';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Bell,
  Wallet,
  Heart,
  Bot,
  User,
  BookOpen,
  TrendingUp,
  AlertTriangle,
  ChevronRight,
  Loader2,
  Activity,
  Clock,
  Shield,
  Coins,
  GraduationCap,
  Ambulance,
  Smartphone,
  Globe,
  Users
} from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const router = useRouter();
  const { user, isFetchingMe: authLoading } = useAuth();

  // جلب البيانات من جميع الـ Stores المكتملة
  const { notifications, unreadCount, fetchNotifications } = useNotificationStore();
  const { wallet, fetchWallet } = useFinanceStore();
  const { agents, fetchAgents } = useAgentStore();
  const { milestones, fetchMilestones } = useDigitalTwinStore();

  // متغيرات مؤقتة لتجاوز فحص TypeScript حتى تكتمل قطاعات الصحة والأكاديمية
  const currentEmergency: any = null;
  const courses: any[] = [];

  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState({
    totalAgents: 0,
    activeAgents: 0,
    totalMilestones: 0,
    totalCourses: 0,
    unreadNotifications: 0,
    balance: 0,
    emergencyStatus: null as string | null,
  });

  // جلب جميع البيانات عند تحميل الصفحة
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        await Promise.all([
          fetchNotifications(),
          fetchWallet(),
          fetchAgents(),
          fetchMilestones(),
          //fetchCourses({ skip: 0, limit: 10 }),
        ]);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, [
    fetchNotifications,
    fetchWallet,
    fetchAgents,
    fetchMilestones,
  ]);

  // ✅ تحديث الإحصائيات بأمان (تم إصلاح الحلقة اللانهائية)
  useEffect(() => {
    const newStats = {
      totalAgents: agents?.length || 0,
      activeAgents: agents?.filter(a => a.status === 'ACTIVE').length || 0,
      totalMilestones: milestones?.length || 0,
      totalCourses: courses?.length || 0,
      unreadNotifications: unreadCount || 0,
      balance: wallet?.balances?.MR_USDT || 0,
      emergencyStatus: currentEmergency?.status || null,
    };

    // التحديث يحدث فقط إذا تغيرت القيم فعلياً
    setStats(prev => JSON.stringify(prev) === JSON.stringify(newStats) ? prev : newStats);
  }, [agents, milestones, unreadCount, wallet]); // أزلنا courses و currentEmergency مؤقتاً

  if (authLoading || isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-64 mt-6" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-7xl">
      {/* الترحيب */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            مرحباً، {user?.name_ar || user?.name_en || 'مستخدم'} 👋
          </h1>
          <p className="text-muted-foreground">
            إليك نظرة عامة على نشاطك وإحصائياتك في المنصة السيادية
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push('/dashboard/health/emergency')} className="bg-red-50 hover:bg-red-100 text-red-700 border-red-200">
            <Ambulance className="mr-2 h-4 w-4" />
            طوارئ
          </Button>
          <Button variant="outline" onClick={() => router.push('/dashboard/notifications')} className="relative">
            <Bell className="mr-2 h-4 w-4" />
            الإشعارات
            {stats.unreadNotifications > 0 && (
              <Badge className="absolute -top-2 -right-2 h-5 w-5 flex items-center justify-center p-0 bg-red-500 text-white text-xs">
                {stats.unreadNotifications}
              </Badge>
            )}
          </Button>
        </div>
      </div>

      {/* البطاقات الإحصائية */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">الرصيد (MR_USDT)</p>
                <p className="text-2xl font-bold">{stats.balance.toFixed(2)}</p>
              </div>
              <div className="p-3 bg-primary/10 rounded-full">
                <Wallet className="h-6 w-6 text-primary" />
              </div>
            </div>
          </CardContent>
          <CardFooter className="pt-0">
            <Button variant="ghost" size="sm" className="w-full justify-center" onClick={() => router.push('/dashboard/finance/wallet')}>
              إدارة المحفظة <ChevronRight className="mr-2 h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">الوكلاء النشطون</p>
                <p className="text-2xl font-bold">{stats.activeAgents} / {stats.totalAgents}</p>
              </div>
              <div className="p-3 bg-purple-500/10 rounded-full">
                <Bot className="h-6 w-6 text-purple-500" />
              </div>
            </div>
          </CardContent>
          <CardFooter className="pt-0">
            <Button variant="ghost" size="sm" className="w-full justify-center" onClick={() => router.push('/dashboard/ai-agents')}>
              إدارة الوكلاء <ChevronRight className="mr-2 h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">الأحداث الحياتية</p>
                <p className="text-2xl font-bold">{stats.totalMilestones}</p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-full">
                <User className="h-6 w-6 text-blue-500" />
              </div>
            </div>
          </CardContent>
          <CardFooter className="pt-0">
            <Button variant="ghost" size="sm" className="w-full justify-center" onClick={() => router.push('/dashboard/digital-twin')}>
              عرض الملف <ChevronRight className="mr-2 h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">الكورسات</p>
                <p className="text-2xl font-bold">{stats.totalCourses}</p>
              </div>
              <div className="p-3 bg-green-500/10 rounded-full">
                <GraduationCap className="h-6 w-6 text-green-500" />
              </div>
            </div>
          </CardContent>
          <CardFooter className="pt-0">
            <Button variant="ghost" size="sm" className="w-full justify-center" onClick={() => router.push('/dashboard/academy')}>
              استكشاف <ChevronRight className="mr-2 h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>
      </div>

      {/* الصف الثاني: حالة الطوارئ والإشعارات */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* حالة الطوارئ */}
        <Card className="md:col-span-1 border-red-200 bg-red-50/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-red-700 flex items-center gap-2 text-base">
              <AlertTriangle className="h-5 w-5" />
              حالة الطوارئ
            </CardTitle>
          </CardHeader>
          <CardContent>
            {currentEmergency ? (
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">البلاغ #{currentEmergency.id}</span>
                  <Badge variant="default" className={currentEmergency?.status === 'COMPLETED' ? 'bg-green-500 text-white' : ''}>
                    {currentEmergency.status === 'PENDING' && 'قيد الانتظار'}
                    {currentEmergency.status === 'DISPATCHED' && 'تم الإرسال'}
                    {currentEmergency.status === 'ON_SCENE' && 'في الموقع'}
                    {currentEmergency.status === 'IN_TRANSIT' && 'في الطريق'}
                    {currentEmergency.status === 'COMPLETED' && 'مكتمل'}
                    {currentEmergency.status === 'CANCELLED' && 'ملغى'}
                  </Badge>
                </div>
                <p className="text-sm">{currentEmergency.emergency_type}</p>
                <Button variant="outline" size="sm" className="w-full" onClick={() => router.push(`/dashboard/health/emergency/${currentEmergency.id}`)}>
                  متابعة
                </Button>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-muted-foreground">لا توجد حالات طوارئ نشطة</p>
                <Button size="sm" className="mt-2 bg-red-600 hover:bg-red-700 text-white" onClick={() => router.push('/dashboard/health/emergency')}>
                  <Ambulance className="mr-2 h-4 w-4" />
                  استدعاء الطوارئ
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* آخر الإشعارات */}
        <Card className="md:col-span-2">
          <CardHeader className="pb-2 flex flex-row justify-between items-center">
            <CardTitle className="text-base flex items-center gap-2">
              <Bell className="h-5 w-5" />
              آخر الإشعارات
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => router.push('/dashboard/communications/notifications')}>
              عرض الكل
            </Button>
          </CardHeader>
          <CardContent>
            {notifications?.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">لا توجد إشعارات جديدة</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {notifications?.slice(0, 5).map((notif) => (
                  <div key={notif.id} className={`flex items-start gap-3 p-2 rounded-lg ${!notif.is_read ? 'bg-muted' : ''}`}>
                    <div className={`w-2 h-2 rounded-full mt-2 ${!notif.is_read ? 'bg-blue-500' : 'bg-gray-300'}`} />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{notif.title}</p>
                      <p className="text-xs text-muted-foreground line-clamp-1">{notif.body}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {new Date(notif.created_at).toLocaleString('ar-EG')}
                      </p>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {notif.priority}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* الصف الثالث: التوأم الرقمي والوكلاء */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* الأحداث الحياتية الأخيرة */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Clock className="h-5 w-5" />
              الأحداث الحياتية الأخيرة
            </CardTitle>
          </CardHeader>
          <CardContent>
            {milestones?.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">لم يتم تسجيل أحداث بعد</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {milestones?.slice(0, 5).map((milestone) => (
                  <div key={milestone.id} className="flex items-center gap-3 p-2 border-b last:border-0">
                    <div className="p-1.5 bg-primary/10 rounded-full">
                      {milestone.milestone_type === 'BIRTH' && <Heart className="h-4 w-4 text-red-500" />}
                      {milestone.milestone_type === 'GRADUATION' && <GraduationCap className="h-4 w-4 text-blue-500" />}
                      {milestone.milestone_type === 'MARRIAGE' && <Users className="h-4 w-4 text-pink-500" />}
                      {milestone.milestone_type === 'PATENT' && <Shield className="h-4 w-4 text-yellow-500" />}
                      {milestone.milestone_type === 'IDENTITY_RESERVATION' && <Shield className="h-4 w-4 text-purple-500" />}
                      {milestone.milestone_type === 'DECEASE_CONFIRMATION' && <Clock className="h-4 w-4 text-gray-500" />}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{milestone.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(milestone.occurrence_date).toLocaleDateString('ar-EG')}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <Button variant="ghost" size="sm" className="w-full mt-2" onClick={() => router.push('/dashboard/digital-twin')}>
              عرض الملف الكامل <ChevronRight className="mr-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>

        {/* الوكلاء النشطون */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Bot className="h-5 w-5" />
              الوكلاء النشطون
            </CardTitle>
          </CardHeader>
          <CardContent>
            {agents?.filter(a => a.status === 'ACTIVE').length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">لا توجد وكلاء نشطون</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {agents?.filter(a => a.status === 'ACTIVE').slice(0, 5).map((agent) => (
                  <div key={agent.id} className="flex items-center justify-between p-2 border rounded-lg">
                    <div>
                      <p className="text-sm font-medium">{agent.name}</p>
                      <p className="text-xs text-muted-foreground">{agent.role}</p>
                    </div>
                    <Badge variant="default" className="bg-green-500">نشط</Badge>
                  </div>
                ))}
              </div>
            )}
            <Button variant="ghost" size="sm" className="w-full mt-2" onClick={() => router.push('/dashboard/ai-agents')}>
              إدارة الوكلاء <ChevronRight className="mr-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* الصف الرابع: روابط سريعة */}
      <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Link href="/dashboard/finance/wallet" className="block">
          <Button variant="outline" className="w-full justify-start">
            <Coins className="mr-2 h-4 w-4" /> المحفظة
          </Button>
        </Link>
        <Link href="/dashboard/academy" className="block">
          <Button variant="outline" className="w-full justify-start">
            <GraduationCap className="mr-2 h-4 w-4" /> الأكاديمية
          </Button>
        </Link>
        <Link href="/dashboard/health" className="block">
          <Button variant="outline" className="w-full justify-start">
            <Heart className="mr-2 h-4 w-4" /> الصحة
          </Button>
        </Link>
        <Link href="/dashboard/digital-twin" className="block">
          <Button variant="outline" className="w-full justify-start">
            <User className="mr-2 h-4 w-4" /> التوأم الرقمي
          </Button>
        </Link>
        <Link href="/dashboard/social" className="block">
          <Button variant="outline" className="w-full justify-start">
            <Globe className="mr-2 h-4 w-4" /> الاجتماعي
          </Button>
        </Link>
        <Link href="/dashboard/settings" className="block">
          <Button variant="outline" className="w-full justify-start">
            <Activity className="mr-2 h-4 w-4" /> الإعدادات
          </Button>
        </Link>
      </div>
    </div>
  );
}