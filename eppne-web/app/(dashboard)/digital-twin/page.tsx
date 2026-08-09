// app/(dashboard)/digital-twin/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useDigitalTwinStore } from '@/store/digitalTwinStore';
import { useAuth } from '@/hooks/identity/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { 
  User, 
  Settings, 
  Clock, 
  Heart, 
  GraduationCap, 
  Coins, 
  Bot, 
  Loader2,
  Plus,
  Calendar,
  FileText,
  Shield,
  Wallet,
  Link2,
  Globe,
  Lock,
  Users,
  Gift
} from 'lucide-react';

export default function DigitalTwinPage() {
  const { user } = useAuth();
  const {
    config,
    timeCapsule,
    milestones,
    isLoading,
    fetchConfig,
    fetchTimeCapsule,
    fetchMilestones,
    updateConfig,
    sendHeartbeat,
    addMilestone,
  } = useDigitalTwinStore();

  const [isConfigDialogOpen, setIsConfigDialogOpen] = useState(false);
  const [isMilestoneDialogOpen, setIsMilestoneDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // إعدادات النموذج
  const [editConfig, setEditConfig] = useState({
    global_access_level: 'PRIVATE' as any,
    interaction_fee_mrusdt: 0,
    subscription_monthly_mrusdt: 0,
    capabilities: ['CHAT'] as ('CHAT' | 'MEETING' | 'FINANCE' | 'SIGN' | 'LEGACY')[],
    max_spending_limit: 0,
    settlement_type: 'WEB2_FIAT',
  });

  const [newMilestone, setNewMilestone] = useState({
    milestone_type: 'GRADUATION' as any,
    title: '',
    description: '',
    occurrence_date: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    fetchConfig();
    fetchTimeCapsule();
    fetchMilestones();
  }, [fetchConfig, fetchTimeCapsule, fetchMilestones]);

  const handleUpdateConfig = async () => {
    setIsSubmitting(true);
    try {
      await updateConfig(editConfig);
      toast.success('تم تحديث إعدادات التوأم الرقمي');
      setIsConfigDialogOpen(false);
    } catch (error: any) {
      toast.error(error.message || 'فشل تحديث الإعدادات');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddMilestone = async () => {
    if (!newMilestone.title.trim()) {
      toast.error('يرجى إدخال عنوان الحدث');
      return;
    }
    setIsSubmitting(true);
    try {
      await addMilestone({
        ...newMilestone,
        occurrence_date: new Date(newMilestone.occurrence_date).toISOString(),
      });
      toast.success('تم إضافة الحدث الحياتي بنجاح');
      setIsMilestoneDialogOpen(false);
      setNewMilestone({
        milestone_type: 'GRADUATION',
        title: '',
        description: '',
        occurrence_date: new Date().toISOString().split('T')[0],
      });
    } catch (error: any) {
      toast.error(error.message || 'فشل إضافة الحدث');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendHeartbeat = async () => {
    try {
      await sendHeartbeat();
      toast.success('تم إرسال نبضة القلب بنجاح');
    } catch (error: any) {
      toast.error(error.message || 'فشل إرسال نبضة القلب');
    }
  };

  if (isLoading && !config) {
    return (
      <div className="container mx-auto py-8 max-w-4xl">
        <Skeleton className="h-8 w-48 mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-64 mt-6" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-5xl">
      {/* الهيدر */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <User className="h-6 w-6" />
            التوأم الرقمي
            {config?.is_active && (
              <Badge variant="default" className="ml-2 bg-green-500">نشط</Badge>
            )}
          </h1>
          <p className="text-muted-foreground text-sm">
            ملفك الرقمي المتكامل الذي يربط جميع جوانب حياتك الرقمية
          </p>
        </div>
        <Button variant="outline" onClick={() => setIsConfigDialogOpen(true)}>
          <Settings className="mr-2 h-4 w-4" />
          إعدادات
        </Button>
      </div>

      {/* البطاقات الإحصائية */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-full">
                <Clock className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">الأحداث الحياتية</p>
                <p className="text-2xl font-bold">{milestones.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/10 rounded-full">
                <Heart className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">الحالة الصحية</p>
                <p className="text-2xl font-bold text-green-500">جيد</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-500/10 rounded-full">
                <Coins className="h-5 w-5 text-yellow-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">الرصيد</p>
                <p className="text-2xl font-bold">$1,234.56</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/10 rounded-full">
                <Bot className="h-5 w-5 text-purple-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">الوكلاء النشطون</p>
                <p className="text-2xl font-bold">{config?.agent_id ? '1' : '0'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* التبويبات */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">نظرة عامة</TabsTrigger>
          <TabsTrigger value="milestones">الأحداث الحياتية</TabsTrigger>
          <TabsTrigger value="time-capsule">كبسولة الزمن</TabsTrigger>
          <TabsTrigger value="capabilities">الإمكانيات</TabsTrigger>
        </TabsList>

        {/* ============================================ */}
        {/* علامة تبويب: نظرة عامة */}
        {/* ============================================ */}
        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>ملف التوأم الرقمي</CardTitle>
              <CardDescription>
                {config?.global_access_level === 'PUBLIC' && 'هذا الملف عام للجميع'}
                {config?.global_access_level === 'FAMILY' && 'هذا الملف متاح للعائلة فقط'}
                {config?.global_access_level === 'PAID_ONLY' && 'هذا الملف متاح للدفع فقط'}
                {config?.global_access_level === 'PRIVATE' && 'هذا الملف خاص بك فقط'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">الاسم</p>
                  <p className="font-medium">{user?.name_ar || user?.name_en || 'غير محدد'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">المعرف</p>
                  <p className="font-medium">#{user?.id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">الرتبة السيادية</p>
                  <p className="font-medium">{user?.sovereign_rank || 'غير محدد'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">حالة التوأم</p>
                  <p className="font-medium">
                    {config?.is_active ? '🟢 نشط' : '🔴 غير نشط'}
                  </p>
                </div>
              </div>
              <div className="border-t pt-4">
                <p className="text-sm text-muted-foreground">الإمكانيات النشطة</p>
                <div className="flex flex-wrap gap-2 mt-2">
                  {config?.capabilities?.map((cap) => (
                    <Badge key={cap} variant="outline">
                      {cap === 'CHAT' && '💬 محادثة'}
                      {cap === 'MEETING' && '📹 اجتماع'}
                      {cap === 'FINANCE' && '💰 مالية'}
                      {cap === 'SIGN' && '✍️ توقيع'}
                      {cap === 'LEGACY' && '📜 إرث'}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ============================================ */}
        {/* علامة تبويب: الأحداث الحياتية */}
        {/* ============================================ */}
        <TabsContent value="milestones">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>الأحداث الحياتية</CardTitle>
                <CardDescription>سجل رحلتك الرقمية من البداية</CardDescription>
              </div>
              <Dialog open={isMilestoneDialogOpen} onOpenChange={setIsMilestoneDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm">
                    <Plus className="mr-2 h-4 w-4" />
                    إضافة حدث
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>إضافة حدث حياتي جديد</DialogTitle>
                    <DialogDescription>
                      سجل حدثاً مهماً في رحلتك الرقمية
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>نوع الحدث *</Label>
                      <Select
                        value={newMilestone.milestone_type}
                        onValueChange={(value) => setNewMilestone({ ...newMilestone, milestone_type: value as any })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="اختر نوع الحدث" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="IDENTITY_RESERVATION">حجز الهوية</SelectItem>
                          <SelectItem value="BIRTH">الميلاد</SelectItem>
                          <SelectItem value="GRADUATION">التخرج</SelectItem>
                          <SelectItem value="MARRIAGE">الزواج</SelectItem>
                          <SelectItem value="PATENT">براءة اختراع</SelectItem>
                          <SelectItem value="DECEASE_CONFIRMATION">تأكيد الوفاة</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>العنوان *</Label>
                      <Input
                        placeholder="عنوان الحدث"
                        value={newMilestone.title}
                        onChange={(e) => setNewMilestone({ ...newMilestone, title: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>الوصف</Label>
                      <Textarea
                        placeholder="وصف الحدث..."
                        value={newMilestone.description}
                        onChange={(e) => setNewMilestone({ ...newMilestone, description: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>التاريخ *</Label>
                      <Input
                        type="date"
                        value={newMilestone.occurrence_date}
                        onChange={(e) => setNewMilestone({ ...newMilestone, occurrence_date: e.target.value })}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsMilestoneDialogOpen(false)}>إلغاء</Button>
                    <Button onClick={handleAddMilestone} disabled={isSubmitting}>
                      {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      إضافة الحدث
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {milestones.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                  <p>لا توجد أحداث حياتية مسجلة</p>
                  <p className="text-sm">أضف أول حدث لتوثيق رحلتك الرقمية</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {milestones.map((milestone) => (
                    <div key={milestone.id} className="flex items-start gap-4 border-b pb-4">
                      <div className="p-2 bg-primary/10 rounded-full">
                        {milestone.milestone_type === 'BIRTH' && <Heart className="h-5 w-5 text-red-500" />}
                        {milestone.milestone_type === 'GRADUATION' && <GraduationCap className="h-5 w-5 text-blue-500" />}
                        {milestone.milestone_type === 'MARRIAGE' && <Users className="h-5 w-5 text-pink-500" />}
                        {milestone.milestone_type === 'PATENT' && <FileText className="h-5 w-5 text-yellow-500" />}
                        {milestone.milestone_type === 'IDENTITY_RESERVATION' && <Shield className="h-5 w-5 text-purple-500" />}
                        {milestone.milestone_type === 'DECEASE_CONFIRMATION' && <Clock className="h-5 w-5 text-gray-500" />}
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{milestone.title}</p>
                            <p className="text-sm text-muted-foreground">{milestone.description}</p>
                          </div>
                          <Badge variant="outline">
                            {new Date(milestone.occurrence_date).toLocaleDateString('ar-EG')}
                          </Badge>
                        </div>
                        {milestone.milestone_nft_id && (
                          <div className="mt-1 text-xs text-muted-foreground">
                            NFT: {milestone.milestone_nft_id.substring(0, 16)}...
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ============================================ */}
        {/* علامة تبويب: كبسولة الزمن */}
        {/* ============================================ */}
        <TabsContent value="time-capsule">
          <Card>
            <CardHeader>
              <CardTitle>كبسولة الزمن</CardTitle>
              <CardDescription>
                تحتفظ ببياناتك المهمة التي ستُفتح في المستقبل
              </CardDescription>
            </CardHeader>
            <CardContent>
              {timeCapsule ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">الحالة</p>
                      <p className="font-medium">
                        <Badge variant={timeCapsule.status === 'ACTIVE' ? 'default' : 'secondary'}>
                          {timeCapsule.status === 'ACTIVE' ? 'نشطة' : 'غير نشطة'}
                        </Badge>
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">آخر نبضة قلب</p>
                      <p className="font-medium">
                        {new Date(timeCapsule.last_heartbeat_at).toLocaleString('ar-EG')}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">فترة النبض</p>
                      <p className="font-medium">{timeCapsule.heartbeat_interval_days || 90} يوم</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">التشفير</p>
                      <p className="font-medium">
                        {timeCapsule.encrypted_payload_hash ? '✅ مشفر' : '❌ غير مشفر'}
                      </p>
                    </div>
                  </div>
                  <div className="border-t pt-4">
                    <Button onClick={handleSendHeartbeat} variant="outline">
                      <Heart className="mr-2 h-4 w-4" />
                      إرسال نبضة قلب
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                  <p>لا توجد كبسولة زمنية</p>
                  <p className="text-sm">أنشئ كبسولة زمنية لحماية إرثك الرقمي</p>
                  <Button className="mt-4" variant="outline" onClick={() => window.location.href = '/dashboard/digital-twin/time-capsule'}>
                    <Plus className="mr-2 h-4 w-4" />
                    إنشاء كبسولة
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ============================================ */}
        {/* علامة تبويب: الإمكانيات */}
        {/* ============================================ */}
        <TabsContent value="capabilities">
          <Card>
            <CardHeader>
              <CardTitle>إمكانيات التوأم الرقمي</CardTitle>
              <CardDescription>
                الميزات المتاحة للتفاعل مع التوأم الرقمي
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {config?.capabilities?.map((cap) => (
                  <div key={cap} className="flex items-center gap-3 p-3 border rounded-lg">
                    {cap === 'CHAT' && <Bot className="h-5 w-5 text-primary" />}
                    {cap === 'MEETING' && <Users className="h-5 w-5 text-blue-500" />}
                    {cap === 'FINANCE' && <Coins className="h-5 w-5 text-yellow-500" />}
                    {cap === 'SIGN' && <FileText className="h-5 w-5 text-green-500" />}
                    {cap === 'LEGACY' && <Clock className="h-5 w-5 text-purple-500" />}
                    <div>
                      <p className="font-medium">
                        {cap === 'CHAT' && 'المحادثة'}
                        {cap === 'MEETING' && 'الاجتماعات'}
                        {cap === 'FINANCE' && 'المالية'}
                        {cap === 'SIGN' && 'التوقيع'}
                        {cap === 'LEGACY' && 'الإرث'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {cap === 'CHAT' && 'التواصل النصي والصوتي مع التوأم'}
                        {cap === 'MEETING' && 'عقد اجتماعات افتراضية'}
                        {cap === 'FINANCE' && 'إدارة المعاملات المالية'}
                        {cap === 'SIGN' && 'التوقيع الرقمي على العقود'}
                        {cap === 'LEGACY' && 'إدارة الإرث الرقمي والوصايا'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ============================================ */}
      {/* حوار إعدادات التوأم الرقمي */}
      {/* ============================================ */}
      <Dialog open={isConfigDialogOpen} onOpenChange={setIsConfigDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>إعدادات التوأم الرقمي</DialogTitle>
            <DialogDescription>
              تحكم في مستوى الوصول، الإمكانيات، والحدود المالية للتوأم الرقمي الخاص بك
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>مستوى الوصول</Label>
                <Select
                  value={editConfig.global_access_level}
                  onValueChange={(value) => setEditConfig({ ...editConfig, global_access_level: value as any })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="اختر مستوى الوصول" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PRIVATE">🔒 خاص</SelectItem>
                    <SelectItem value="FAMILY">👪 العائلة</SelectItem>
                    <SelectItem value="PAID_ONLY">💰 مدفوع</SelectItem>
                    <SelectItem value="PUBLIC">🌍 عام</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>نوع التسوية</Label>
                <Select
                  value={editConfig.settlement_type}
                  onValueChange={(value) => setEditConfig({ ...editConfig, settlement_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="اختر نوع التسوية" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="WEB2_FIAT">💳 فيات (بنكي)</SelectItem>
                    <SelectItem value="WEB3_CRYPTO">₿ عملات رقمية</SelectItem>
                    <SelectItem value="HYBRID">🔀 هجين</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>رسوم التفاعل (MR_USDT)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={editConfig.interaction_fee_mrusdt}
                  onChange={(e) => setEditConfig({ ...editConfig, interaction_fee_mrusdt: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>الاشتراك الشهري (MR_USDT)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={editConfig.subscription_monthly_mrusdt}
                  onChange={(e) => setEditConfig({ ...editConfig, subscription_monthly_mrusdt: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>الحد الأقصى للإنفاق (MR_USDT)</Label>
              <Input
                type="number"
                step="0.01"
                min="0"
                value={editConfig.max_spending_limit}
                onChange={(e) => setEditConfig({ ...editConfig, max_spending_limit: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="space-y-2">
              <Label>الإمكانيات</Label>
              <div className="grid grid-cols-2 gap-2">
                {(['CHAT', 'MEETING', 'FINANCE', 'SIGN', 'LEGACY'] as const).map((cap) => (
                  <div key={cap} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={`cap-${cap}`}
                      checked={editConfig.capabilities.includes(cap)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setEditConfig({
                            ...editConfig,
                            capabilities: [...editConfig.capabilities, cap],
                          });
                        } else {
                          setEditConfig({
                            ...editConfig,
                            capabilities: editConfig.capabilities.filter((c) => c !== cap),
                          });
                        }
                      }}
                      className="w-4 h-4"
                    />
                    <Label htmlFor={`cap-${cap}`} className="text-sm">
                      {cap === 'CHAT' && '💬 محادثة'}
                      {cap === 'MEETING' && '📹 اجتماع'}
                      {cap === 'FINANCE' && '💰 مالية'}
                      {cap === 'SIGN' && '✍️ توقيع'}
                      {cap === 'LEGACY' && '📜 إرث'}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsConfigDialogOpen(false)}>إلغاء</Button>
            <Button onClick={handleUpdateConfig} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              حفظ الإعدادات
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}