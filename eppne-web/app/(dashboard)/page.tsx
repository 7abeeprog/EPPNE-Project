// app/(dashboard)/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/auth/useAuth';
import { useNotificationStore } from '@/store/notificationStore';
import { useFinanceStore } from '@/store/financeStore';
import { useHealthStore } from '@/store/healthStore';
import { useAgentStore } from '@/store/agentStore';
import { useDigitalTwinStore } from '@/store/digitalTwinStore';
import { useWebSocket } from '@/components/websocket-provider';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { 
  Bell, 
  Coins, 
  Heart, 
  Bot, 
  User, 
  Activity, 
  TrendingUp, 
  Calendar, 
  MessageSquare,
  AlertCircle,
  CheckCircle,
  Loader2,
  ArrowUpRight,
  Users,
  GraduationCap,
  Building2,
  Truck,
  Shield,
  Clock
} from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();
  const { isConnected } = useWebSocket();

  // الـ Stores
  const { notifications, unreadCount, fetchNotifications } = useNotificationStore();
  const { balances, transactions, fetchWallet, fetchTransactionHistory } = useFinanceStore();
  const { currentEmergency } = useHealthStore();
  const { agents, fetchAgents } = useAgentStore();
  const { config, milestones, fetchConfig, fetchMilestones } = useDigitalTwinStore();

  const [isLoading, setIsLoading] = useState(true);

  // جلب جميع البيانات عند تحميل الصفحة
  useEffect(() => {
    const fetchAllData = async () => {
      setIsLoading(true);
      try {
        await Promise.all([
          fetchNotifications({ is_read: false, limit: 10 }),
          fetchWallet(),
          fetchTransactionHistory(0, 5),
          fetchAgents({ status: 'ACTIVE' }),
          fetchConfig(),
          fetchMilestones(),
        ]);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAllData();
  }, [
    fetchNotifications,
    fetchWallet,
    fetchTransactionHistory,
    fetchAgents,
    fetchConfig,
    fetchMilestones,
  ]);

  // تحديث البيانات كل 30 ثانية
  useEffect(() => {
    const interval = setInterval(() => {
      fetchWallet();
      fetchNotifications({ is_read: false, limit: 10 });
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchWallet, fetchNotifications]);

  // ==========================================
  // مكونات البطاقات
  // ==========================================

  const MetricCard = ({ icon: Icon, title, value, subtitle, trend, href }: any) => (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-full">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <p className="text-sm text-muted-foreground">{title}</p>
          </div>
          {trend && (
            <Badge variant="default" className="bg-green-100 text-green-700">
              <TrendingUp className="h-3 w-3 mr-1" />
              {trend}
            </Badge>
          )}
        </div>
        <div className="mt-2">
          <p className="text-2xl font-bold">{value}</p>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        {href && (
          <Button variant="ghost" size="sm" className="mt-2 p-0 h-auto" onClick={() => window.location.href = href}>
            عرض التفاصيل <ArrowUpRight className="h-3 w-3 ml-1" />
          </Button>
        )}
      </CardContent>
    </Card>
  );

  const QuickActionCard = ({ icon: Icon, title, description, href, color }: any) => (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => window.location.href = href}>
      <CardContent className="pt-6 text-center">
        <div className={`p-3 ${color} rounded-full w-fit mx-auto`}>
          <Icon className="h-6 w-6" />
        </div>
        <p className="font-medium mt-2">{title}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );

  const RecentActivity = ({ items }: any) => (
    <div className="space-y-3 max-h-80 overflow-y-auto">
      {items.map((item: any, index: number) => (
        <div key={index} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
          <div className="p-1.5 bg-primary/10 rounded-full">
            {item.type === 'notification' && <Bell className="h-4 w-4 text-primary" />}
            {item.type === 'transaction' && <Coins className="h-4 w-4 text-yellow-500" />}
            {item.type === 'milestone' && <Calendar className="h-4 w-4 text-blue-500" />}
            {item.type === 'agent' && <Bot className="h-4 w-4 text-purple-500" />}
          </div>
          <div className="flex-1">
            <p className="text-sm">{item.title}</p>
            <p className="text-xs text-muted-foreground">{item.time}</p>
          </div>
          {item.status && (
            <Badge variant={item.status === 'completed' ? 'default' : 'secondary'}>
              {item.status === 'completed' ? 'مكتمل' : 'قيد الانتظار'}
            </Badge>
          )}
        </div>
      ))}
    </div>
  );

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 max-w-7xl">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          <Skeleton className="h-64 col-span-2" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  // تجميع الأنشطة الأخيرة
  const recentActivities = [
    ...notifications.slice(0, 3).map(n => ({
      type: 'notification',
      title: n.title,
      time: new Date(n.created_at).toLocaleString('ar-EG'),
      status: n.is_read ? 'completed' : 'pending',
    })),
    ...transactions.slice(0, 2).map(t => ({
      type: 'transaction',
      title: `${t.tx_type} - ${t.amount} ${t.currency}`,
      time: new Date(t.created_at).toLocaleString('ar-EG'),
      status: t.status === 'COMPLETED' ? 'completed' : 'pending',
    })),
    ...milestones.slice(0, 2).map(m => ({
      type: 'milestone',
      title: m.title,
      time: new Date(m.occurrence_date).toLocaleString('ar-EG'),
      status: m.milestone_nft_id ? 'completed' : 'pending',
    })),
  ].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());

  return (
    <div className="container mx-auto py-8 max-w-7xl">
      {/* الهيدر */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            مرحباً، {user?.name_ar || user?.name_en || 'مستخدم'}
            {isConnected ? (
              <Badge variant="default" className="bg-green-500 text-xs">
                <span className="h-1.5 w-1.5 bg-white rounded-full mr-1 animate-pulse" />
                مباشر
              </Badge>
            ) : (
              <Badge variant="outline" className="text-xs text-red-500">
                <span className="h-1.5 w-1.5 bg-red-500 rounded-full mr-1" />
                غير متصل
              </Badge>
            )}
          </h1>
          <p className="text-muted-foreground text-sm">
            {new Date().toLocaleDateString('ar-EG', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => window.location.href = '/dashboard/notifications'}>
            <Bell className="h-4 w-4 mr-2" />
            {unreadCount > 0 && (
              <span className="bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
                {unreadCount}
              </span>
            )}
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.location.href = '/dashboard/profile'}>
            <User className="h-4 w-4 mr-2" />
            الملف الشخصي
          </Button>
        </div>
      </div>

      {/* البطاقات الإحصائية */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <MetricCard
          icon={Coins}
          title="الرصيد"
          value={balances ? Object.values(balances).reduce((a, b) => a + b, 0).toFixed(2) : '0.00'}
          subtitle={`${balances ? Object.keys(balances).join(', ') : 'لا توجد عملات'}`}
          trend="+12.5%"
          href="/dashboard/finance/wallet"
        />
        <MetricCard
          icon={Bell}
          title="الإشعارات"
          value={unreadCount}
          subtitle={`${notifications.length} إشعار حديث`}
          href="/dashboard/communications/notifications"
        />
        <MetricCard
          icon={Bot}
          title="الوكلاء النشطون"
          value={agents.filter(a => a.status === 'ACTIVE').length}
          subtitle={`إجمالي ${agents.length} وكيل`}
          href="/dashboard/ai-agents"
        />
        <MetricCard
          icon={Calendar}
          title="الأحداث الحياتية"
          value={milestones.length}
          subtitle={`آخر حدث: ${milestones[0]?.title || 'لا يوجد'}`}
          href="/dashboard/digital-twin"
        />
      </div>

      {/* حالة الطوارئ (إذا كانت موجودة) */}
      {currentEmergency && (
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardContent className="pt-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-full animate-pulse">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="font-bold text-red-700">🚨 حالة طوارئ نشطة</p>
                <p className="text-sm text-red-600">
                  النوع: {currentEmergency.emergency_type} • الحالة: {currentEmergency.status}
                </p>
              </div>
            </div>
            <Button variant="outline" className="border-red-300 text-red-700 hover:bg-red-100" onClick={() => window.location.href = `/dashboard/health/emergency/${currentEmergency.id}`}>
              متابعة
            </Button>
          </CardContent>
        </Card>
      )}

      {/* الروابط السريعة والأنشطة */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* العمود الأيسر: الأنشطة */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>الأنشطة الأخيرة</CardTitle>
            <CardDescription>أحدث التحديثات في جميع القطاعات</CardDescription>
          </CardHeader>
          <CardContent>
            <RecentActivity items={recentActivities} />
          </CardContent>
        </Card>

        {/* العمود الأيمن: الروابط السريعة */}
        <Card>
          <CardHeader>
            <CardTitle>روابط سريعة</CardTitle>
            <CardDescription>الوصول السريع إلى أهم الصفحات</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              <QuickActionCard
                icon={Heart}
                title="الطوارئ"
                description="استدعاء فوري"
                href="/dashboard/health/emergency"
                color="bg-red-100 text-red-600"
              />
              <QuickActionCard
                icon={Coins}
                title="المحفظة"
                description="التحويل والصرافة"
                href="/dashboard/finance/wallet"
                color="bg-yellow-100 text-yellow-600"
              />
              <QuickActionCard
                icon={Bot}
                title="الوكلاء"
                description="الذكاء الاصطناعي"
                href="/dashboard/ai-agents"
                color="bg-purple-100 text-purple-600"
              />
              <QuickActionCard
                icon={User}
                title="التوأم الرقمي"
                description="الملف الشخصي"
                href="/dashboard/digital-twin"
                color="bg-blue-100 text-blue-600"
              />
              <QuickActionCard
                icon={GraduationCap}
                title="التعليم"
                description="الكورسات والتدريب"
                href="/dashboard/academy"
                color="bg-green-100 text-green-600"
              />
              <QuickActionCard
                icon={Building2}
                title="المنشآت"
                description="إدارة العقارات"
                href="/dashboard/realestate"
                color="bg-orange-100 text-orange-600"
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ملخص القطاعات */}
      <div className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle>ملخص القطاعات</CardTitle>
            <CardDescription>حالة الخدمات النشطة في المنصة</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
              <div className="text-center p-3 bg-muted/30 rounded-lg">
                <Shield className="h-8 w-8 mx-auto text-blue-500" />
                <p className="text-xs font-medium mt-1">الهوية</p>
                <Badge variant="default" className="text-xs mt-1 bg-green-500">نشط</Badge>
              </div>
              <div className="text-center p-3 bg-muted/30 rounded-lg">
                <Coins className="h-8 w-8 mx-auto text-yellow-500" />
                <p className="text-xs font-medium mt-1">المالية</p>
                <Badge variant="default" className="text-xs mt-1 bg-green-500">نشط</Badge>
              </div>
              <div className="text-center p-3 bg-muted/30 rounded-lg">
                <Heart className="h-8 w-8 mx-auto text-red-500" />
                <p className="text-xs font-medium mt-1">الصحة</p>
                <Badge variant="default" className="text-xs mt-1 bg-green-500">نشط</Badge>
              </div>
              <div className="text-center p-3 bg-muted/30 rounded-lg">
                <GraduationCap className="h-8 w-8 mx-auto text-green-500" />
                <p className="text-xs font-medium mt-1">التعليم</p>
                <Badge variant="default" className="text-xs mt-1 bg-green-500">نشط</Badge>
              </div>
              <div className="text-center p-3 bg-muted/30 rounded-lg">
                <Bot className="h-8 w-8 mx-auto text-purple-500" />
                <p className="text-xs font-medium mt-1">الذكاء الاصطناعي</p>
                <Badge variant="default" className="text-xs mt-1 bg-green-500">نشط</Badge>
              </div>
              <div className="text-center p-3 bg-muted/30 rounded-lg">
                <User className="h-8 w-8 mx-auto text-blue-500" />
                <p className="text-xs font-medium mt-1">التوأم الرقمي</p>
                <Badge variant="default" className="text-xs mt-1 bg-green-500">نشط</Badge>
              </div>
              <div className="text-center p-3 bg-muted/30 rounded-lg">
                <Building2 className="h-8 w-8 mx-auto text-orange-500" />
                <p className="text-xs font-medium mt-1">العقارات</p>
                <Badge variant="default" className="text-xs mt-1 bg-green-500">نشط</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}