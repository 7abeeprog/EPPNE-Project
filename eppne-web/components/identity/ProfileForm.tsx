// components/identity/ProfileForm.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useUpdateProfile } from "@/hooks/identity/useUserProfile";
import type { User as UserData } from "@/types/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, Save, User, Mail, Globe, Calendar } from "lucide-react";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ProfileFormProps {
  user?: UserData;
}

export function ProfileForm({ user }: ProfileFormProps) {
  const [nameAr, setNameAr] = useState(user?.name_ar || "");
  const [nameEn, setNameEn] = useState(user?.name_en || "");
  const [email, setEmail] = useState(user?.email || "");
  const birthDate = user?.birth_date?.split("T")[0] || "";
  const [marriageStatus, setMarriageStatus] = useState<string>(user?.marriage_status || "SINGLE");
  const [languagePreference, setLanguagePreference] = useState(user?.language_preference || "ar");

  const updateMutation = useUpdateProfile();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({
      name_ar: nameAr.trim(),
      name_en: nameEn.trim(),
      email: email.trim(),
      marriage_status: marriageStatus as UserData["marriage_status"],
      language_preference: languagePreference,
    });
  };

  return (
    <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
      <CardContent className="p-6 md:p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label className="font-bold text-lg text-foreground flex items-center gap-2">
                <User className="h-4 w-4 text-primary" />
                الاسم بالعربية
              </Label>
              <Input
                value={nameAr}
                onChange={(e) => setNameAr(e.target.value)}
                placeholder="الاسم الكامل بالعربية..."
                className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg rtl:text-right"
                disabled={updateMutation.isPending}
              />
            </div>
            <div className="space-y-2">
              <Label className="font-bold text-lg text-foreground flex items-center gap-2">
                <User className="h-4 w-4 text-primary" />
                الاسم بالإنجليزية
              </Label>
              <Input
                value={nameEn}
                onChange={(e) => setNameEn(e.target.value)}
                placeholder="Full name in English..."
                className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg"
                disabled={updateMutation.isPending}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="font-bold text-lg text-foreground flex items-center gap-2">
              <Mail className="h-4 w-4 text-primary" />
              البريد الإلكتروني
            </Label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="example@domain.com..."
              className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg"
              disabled={updateMutation.isPending}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="space-y-2">
              <Label className="font-bold text-lg text-foreground flex items-center gap-2">
                <Calendar className="h-4 w-4 text-primary" />
                تاريخ الميلاد
              </Label>
              <Input
                type="date"
                value={birthDate}
                readOnly
                disabled
                className="h-14 bg-background/30 border-white/10 rounded-xl shadow-inner text-lg opacity-70 cursor-not-allowed"
              />
              <p className="text-xs text-muted-foreground">
                غير قابل للتعديل من هنا حاليًا (لا يدعمه الباك إند بعد).
              </p>
            </div>
            <div className="space-y-2">
              <Label className="font-bold text-lg text-foreground">الحالة الاجتماعية</Label>
              <Select
                value={marriageStatus}
                onValueChange={setMarriageStatus}
                disabled={updateMutation.isPending}
              >
                <SelectTrigger className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                  <SelectItem value="SINGLE">أعزب</SelectItem>
                  <SelectItem value="MARRIED">متزوج</SelectItem>
                  <SelectItem value="DIVORCED">مطلق</SelectItem>
                  <SelectItem value="WIDOWED">أرمل</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="font-bold text-lg text-foreground flex items-center gap-2">
                <Globe className="h-4 w-4 text-primary" />
                اللغة
              </Label>
              <Select
                value={languagePreference}
                onValueChange={setLanguagePreference}
                disabled={updateMutation.isPending}
              >
                <SelectTrigger className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                  <SelectItem value="ar">العربية</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button
            type="submit"
            disabled={updateMutation.isPending}
            className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all hover:scale-[1.02]"
          >
            {updateMutation.isPending ? (
              <>
                <Loader2 className="ml-2 h-6 w-6 animate-spin" />
                جاري الحفظ...
              </>
            ) : (
              <>
                <Save className="ml-2 h-6 w-6" />
                حفظ التغييرات
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
