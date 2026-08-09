// components/identity/ChangePasswordForm.tsx
"use client";

import { useState } from "react";
import { useChangePassword } from "@/hooks/identity/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, Eye, EyeOff, KeyRound } from "lucide-react";
import { toast } from "sonner";

export function ChangePasswordForm() {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);
  const changePasswordMutation = useChangePassword();

  const passwordsMatch = newPassword === confirmPassword && newPassword.length > 0;
  const isFormValid = oldPassword.length > 0 && newPassword.length >= 8 && passwordsMatch;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) {
      toast.error("يرجى تصحيح جميع الأخطاء في النموذج");
      return;
    }
    changePasswordMutation.mutate(
      { old_password: oldPassword, new_password: newPassword },
      {
        onSuccess: () => {
          setOldPassword("");
          setNewPassword("");
          setConfirmPassword("");
        },
      }
    );
  };

  return (
    <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
      <CardContent className="p-6 md:p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="oldPassword" className="text-lg font-bold text-foreground">
              كلمة المرور الحالية
            </Label>
            <div className="relative">
              <Input
                id="oldPassword"
                type={showPasswords ? "text" : "password"}
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right"
                disabled={changePasswordMutation.isPending}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPasswords(!showPasswords)}
                className="absolute inset-y-0 left-3 flex items-center text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPasswords ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="newPassword" className="text-lg font-bold text-foreground">
              كلمة المرور الجديدة
            </Label>
            <Input
              id="newPassword"
              type={showPasswords ? "text" : "password"}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right"
              disabled={changePasswordMutation.isPending}
              autoComplete="new-password"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmNewPassword" className="text-lg font-bold text-foreground">
              تأكيد كلمة المرور الجديدة
            </Label>
            <Input
              id="confirmNewPassword"
              type={showPasswords ? "text" : "password"}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right"
              disabled={changePasswordMutation.isPending}
              autoComplete="new-password"
            />
          </div>

          <Button
            type="submit"
            disabled={changePasswordMutation.isPending || !isFormValid}
            className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all hover:scale-[1.02]"
          >
            {changePasswordMutation.isPending ? (
              <>
                <Loader2 className="ml-2 h-6 w-6 animate-spin" />
                جاري الحفظ...
              </>
            ) : (
              <>
                <KeyRound className="ml-2 h-6 w-6" />
                تغيير كلمة المرور
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
