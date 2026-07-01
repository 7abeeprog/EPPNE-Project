// app/(dashboard)/health/page.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getMyProfile, getMyAppointments, getAIPrognosis } from '@/services/health';
import { useHealthStore } from '@/store/healthStore';
import BioProfileManager from '@/components/health/BioProfileManager';
import AIPrognosisRadar from '@/components/health/AIPrognosisRadar';
import EmergencySOSButton from '@/components/health/EmergencySOSButton';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Loader2, User, Brain, Calendar, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function HealthDashboard() {
  const { profile, setProfile } = useHealthStore();

  const { data: profileData, isLoading: profileLoading } = useQuery({
    queryKey: ['health-profile'],
    queryFn: () => getMyProfile().then(res => res.data),
    onSuccess: (data) => setProfile(data),
    staleTime: 2 * 60 * 1000,
  });

  const { data: appointments } = useQuery({
    queryKey: ['health-appointments'],
    queryFn: () => getMyAppointments({ status: 'CONFIRMED' }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  if (profileLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 relative">
      {/* زر الطوارئ */}
      <div className="fixed bottom-6 right-6 z-50">
        <EmergencySOSButton />
      </div>

      {/* الهيدر */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🏥 الصحة والطوارئ</h1>
          <p className="text-sm text-muted-foreground/70">إدارة الملفات الطبية، الرصد الحيوي، والطوارئ</p>
        </div>
        <div className="flex items-center gap-2">
          {profile && (
            <span className={cn(
              "text-xs px-3 py-1 rounded-full border",
              profile.health_score > 80 ? "border-emerald-500/30 text-emerald-500" :
              profile.health_score > 50 ? "border-amber-500/30 text-amber-500" :
              "border-red-500/30 text-red-500"
            )}>
              🩺 درجة الصحة: {profile.health_score}
            </span>
          )}
        </div>
      </div>

      {/* التبويبات */}
      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList className="bg-card/20 backdrop-blur-xl border border-white/10 p-1 rounded-2xl">
          <TabsTrigger value="profile" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm">
            <User className="w-4 h-4 mr-1.5" />
            الملف الطبي
          </TabsTrigger>
          <TabsTrigger value="ai" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm">
            <Brain className="w-4 h-4 mr-1.5" />
            توقعات الذكاء الاصطناعي
          </TabsTrigger>
          <TabsTrigger value="appointments" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm">
            <Calendar className="w-4 h-4 mr-1.5" />
            المواعيد
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          {profile && <BioProfileManager profile={profile} />}
        </TabsContent>

        <TabsContent value="ai">
          <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <AIPrognosisRadar />
          </div>
        </TabsContent>

        <TabsContent value="appointments">
          <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <div className="space-y-3">
              {appointments?.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground/60">
                  <Calendar className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p>لا توجد مواعيد قادمة</p>
                </div>
              ) : (
                appointments?.map((app) => (
                  <div key={app.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                    <div>
                      <p className="text-sm font-medium text-foreground/80">موعد #{app.id}</p>
                      <p className="text-xs text-muted-foreground/50">
                        {new Date(app.appointment_time).toLocaleDateString('ar-EG')} - {new Date(app.appointment_time).toLocaleTimeString('ar-EG')}
                      </p>
                    </div>
                    <span className={cn(
                      "text-xs px-2 py-0.5 rounded-full border",
                      app.status === 'CONFIRMED' ? "border-emerald-500/30 text-emerald-500" :
                      app.status === 'CANCELLED' ? "border-red-500/30 text-red-500" :
                      "border-amber-500/30 text-amber-500"
                    )}>
                      {app.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}