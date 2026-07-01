// components/privacy/PrivacySettingsForm.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { PrivacySettings } from "@/types/privacy";
import { useUpdatePrivacySettings } from "@/hooks/privacy/usePrivacySettings";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, Save, Eye, Search, Brain, Megaphone, MapPin } from "lucide-react";

interface PrivacySettingsFormProps {
    initialSettings?: PrivacySettings;
}

export function PrivacySettingsForm({ initialSettings }: PrivacySettingsFormProps) {
    const [settings, setSettings] = useState<Partial<PrivacySettings>>({
        profile_visibility: initialSettings?.profile_visibility || "PUBLIC",
        search_engine_indexing: initialSettings?.search_engine_indexing ?? true,
        allow_ai_training: initialSettings?.allow_ai_training ?? false,
        allow_targeted_ads: initialSettings?.allow_targeted_ads ?? true,
        share_live_location: initialSettings?.share_live_location ?? false,
    });

    const updateMutation = useUpdatePrivacySettings();

    const handleChange = (field: keyof PrivacySettings, value: any) => {
        setSettings((prev) => ({ ...prev, [field]: value }));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        updateMutation.mutate(settings);
    };

    const isDirty = JSON.stringify(settings) !== JSON.stringify({
        profile_visibility: initialSettings?.profile_visibility || "PUBLIC",
        search_engine_indexing: initialSettings?.search_engine_indexing ?? true,
        allow_ai_training: initialSettings?.allow_ai_training ?? false,
        allow_targeted_ads: initialSettings?.allow_targeted_ads ?? true,
        share_live_location: initialSettings?.share_live_location ?? false,
    });

    return (
        <form onSubmit={handleSubmit}>
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
                <CardContent className="p-6 md:p-8 space-y-6">
                    {/* رؤية الملف الشخصي */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 bg-background/40 rounded-xl border border-white/5 hover:border-purple-500/30 transition-colors group"
                    >
                        <div className="flex items-start gap-4">
                            <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20 group-hover:scale-110 transition-transform">
                                <Eye className="h-5 w-5 text-purple-500" />
                            </div>
                            <div>
                                <Label className="font-bold text-lg text-foreground">رؤية الملف الشخصي</Label>
                                <p className="text-sm text-muted-foreground mt-1">
                                    التحكم في من يمكنه رؤية ملفك الشخصي
                                </p>
                            </div>
                        </div>
                        <Select
                            value={settings.profile_visibility}
                            onValueChange={(value) => handleChange('profile_visibility', value)}
                        >
                            <SelectTrigger className="w-full md:w-48 bg-background/50 border-white/10 rounded-xl focus:border-purple-500 shadow-inner">
                                <SelectValue placeholder="اختر الرؤية" />
                            </SelectTrigger>
                            <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                                <SelectItem value="PUBLIC">عام</SelectItem>
                                <SelectItem value="FRIENDS_ONLY">الأصدقاء فقط</SelectItem>
                                <SelectItem value="PRIVATE">خاص</SelectItem>
                            </SelectContent>
                        </Select>
                    </motion.div>

                    {/* فهرسة محركات البحث */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.15 }}
                        className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 bg-background/40 rounded-xl border border-white/5 hover:border-purple-500/30 transition-colors group"
                    >
                        <div className="flex items-start gap-4">
                            <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20 group-hover:scale-110 transition-transform">
                                <Search className="h-5 w-5 text-emerald-500" />
                            </div>
                            <div>
                                <Label className="font-bold text-lg text-foreground">فهرسة محركات البحث</Label>
                                <p className="text-sm text-muted-foreground mt-1">
                                    السماح لمحركات البحث بفهرسة ملفك الشخصي
                                </p>
                            </div>
                        </div>
                        <Switch
                            checked={settings.search_engine_indexing}
                            onCheckedChange={(checked) => handleChange('search_engine_indexing', checked)}
                            className="data-[state=checked]:bg-emerald-500"
                        />
                    </motion.div>

                    {/* تدريب الذكاء الاصطناعي */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 bg-background/40 rounded-xl border border-white/5 hover:border-purple-500/30 transition-colors group"
                    >
                        <div className="flex items-start gap-4">
                            <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20 group-hover:scale-110 transition-transform">
                                <Brain className="h-5 w-5 text-amber-500" />
                            </div>
                            <div>
                                <Label className="font-bold text-lg text-foreground">تدريب الذكاء الاصطناعي</Label>
                                <p className="text-sm text-muted-foreground mt-1">
                                    السماح باستخدام بياناتك لتحسين نماذج الذكاء الاصطناعي
                                </p>
                            </div>
                        </div>
                        <Switch
                            checked={settings.allow_ai_training}
                            onCheckedChange={(checked) => handleChange('allow_ai_training', checked)}
                            className="data-[state=checked]:bg-amber-500"
                        />
                    </motion.div>

                    {/* الإعلانات المخصصة */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.25 }}
                        className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 bg-background/40 rounded-xl border border-white/5 hover:border-purple-500/30 transition-colors group"
                    >
                        <div className="flex items-start gap-4">
                            <div className="p-2 bg-rose-500/10 rounded-lg border border-rose-500/20 group-hover:scale-110 transition-transform">
                                <Megaphone className="h-5 w-5 text-rose-500" />
                            </div>
                            <div>
                                <Label className="font-bold text-lg text-foreground">الإعلانات المخصصة</Label>
                                <p className="text-sm text-muted-foreground mt-1">
                                    السماح بعرض إعلانات مخصصة بناءً على نشاطك
                                </p>
                            </div>
                        </div>
                        <Switch
                            checked={settings.allow_targeted_ads}
                            onCheckedChange={(checked) => handleChange('allow_targeted_ads', checked)}
                            className="data-[state=checked]:bg-rose-500"
                        />
                    </motion.div>

                    {/* مشاركة الموقع الحي */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 bg-background/40 rounded-xl border border-white/5 hover:border-purple-500/30 transition-colors group"
                    >
                        <div className="flex items-start gap-4">
                            <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20 group-hover:scale-110 transition-transform">
                                <MapPin className="h-5 w-5 text-blue-500" />
                            </div>
                            <div>
                                <Label className="font-bold text-lg text-foreground">مشاركة الموقع الحي</Label>
                                <p className="text-sm text-muted-foreground mt-1">
                                    مشاركة موقعك الحالي مع التطبيقات المرتبطة
                                </p>
                            </div>
                        </div>
                        <Switch
                            checked={settings.share_live_location}
                            onCheckedChange={(checked) => handleChange('share_live_location', checked)}
                            className="data-[state=checked]:bg-blue-500"
                        />
                    </motion.div>

                    {/* زر الحفظ */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.35 }}
                        className="flex justify-end pt-6 border-t border-border/50"
                    >
                        <Button
                            type="submit"
                            disabled={!isDirty || updateMutation.isPending}
                            className="h-14 px-10 text-lg font-bold rounded-xl shadow-[0_0_20px_rgba(139,92,246,0.3)] hover:scale-105 transition-transform bg-purple-600 hover:bg-purple-500"
                        >
                            {updateMutation.isPending ? (
                                <Loader2 className="mr-2 h-6 w-6 animate-spin" />
                            ) : (
                                <Save className="mr-2 h-6 w-6" />
                            )}
                            {updateMutation.isPending ? "جاري الحفظ..." : "حفظ الإعدادات"}
                        </Button>
                    </motion.div>
                </CardContent>
            </Card>
        </form>
    );
}