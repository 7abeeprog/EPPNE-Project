// components/identity/RegisterForm.tsx
"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useRegister } from "@/hooks/identity/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, Eye, EyeOff, UserPlus, CheckCircle, XCircle } from "lucide-react";
import { toast } from "sonner";

// ✅ توليد Idempotency Key باستخدام crypto.randomUUID() مع Fallback
const generateIdempotencyKey = (): string => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback لبيئة التطوير
  return `IDEMP-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
};

// ✅ التحقق من قوة كلمة المرور
const validatePassword = (password: string): { valid: boolean; message: string } => {
  if (password.length < 8) {
    return { valid: false, message: "كلمة المرور يجب أن تحتوي على 8 أحرف على الأقل" };
  }
  if (!/[A-Z]/.test(password)) {
    return { valid: false, message: "كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل" };
  }
  if (!/[a-z]/.test(password)) {
    return { valid: false, message: "كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل" };
  }
  if (!/[0-9]/.test(password)) {
    return { valid: false, message: "كلمة المرور يجب أن تحتوي على رقم واحد على الأقل" };
  }
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    return { valid: false, message: "كلمة المرور يجب أن تحتوي على رمز خاص واحد على الأقل" };
  }
  return { valid: true, message: "كلمة مرور قوية" };
};

export function RegisterForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [nameAr, setNameAr] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const registerMutation = useRegister();

  // ✅ توليد Idempotency Key مرة واحدة عند تحميل المكون
  const [idempotencyKey] = useState(() => generateIdempotencyKey());

  const passwordValidation = validatePassword(password);
  const passwordsMatch = password === confirmPassword && password.length > 0;
  const isFormValid =
    username.trim().length > 0 &&
    email.trim().length > 0 &&
    nameAr.trim().length > 0 &&
    nameEn.trim().length > 0 &&
    passwordValidation.valid &&
    passwordsMatch;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) {
      toast.error("يرجى تصحيح جميع الأخطاء في النموذج");
      return;
    }
    registerMutation.mutate({
      username: username.trim(),
      email: email.trim(),
      password,
      name_ar: nameAr.trim(),
      name_en: nameEn.trim(),
      idempotency_key: idempotencyKey, // ✅ المفتاح الثابت
    });
  };

  // ✅ معالجة نجاح التسجيل
  if (registerMutation.isSuccess) {
    toast.success("تم إنشاء الحساب بنجاح! يمكنك تسجيل الدخول الآن. 🎉", { duration: 3000 });
    router.push("/login");
  }

  return (
    <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.2)] rounded-[2rem] overflow-hidden">
      <CardContent className="p-6 md:p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="nameAr" className="text-lg font-bold text-foreground">
                الاسم بالعربية
              </Label>
              <Input
                id="nameAr"
                type="text"
                placeholder="الاسم الكامل بالعربية..."
                value={nameAr}
                onChange={(e) => setNameAr(e.target.value)}
                className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right"
                disabled={registerMutation.isPending}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="nameEn" className="text-lg font-bold text-foreground">
                الاسم بالإنجليزية
              </Label>
              <Input
                id="nameEn"
                type="text"
                placeholder="Full name in English..."
                value={nameEn}
                onChange={(e) => setNameEn(e.target.value)}
                className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg"
                disabled={registerMutation.isPending}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="username" className="text-lg font-bold text-foreground">
              اسم المستخدم
            </Label>
            <Input
              id="username"
              type="text"
              placeholder="أدخل اسم المستخدم..."
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right"
              disabled={registerMutation.isPending}
              autoComplete="username"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" className="text-lg font-bold text-foreground">
              البريد الإلكتروني
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="أدخل بريدك الإلكتروني..."
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right"
              disabled={registerMutation.isPending}
              autoComplete="email"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-lg font-bold text-foreground">
              كلمة المرور
            </Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="أدخل كلمة المرور..."
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right ${
                  password.length > 0 && (passwordValidation.valid ? "border-emerald-500/50" : "border-destructive/50")
                }`}
                disabled={registerMutation.isPending}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 left-3 flex items-center text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
            {password.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex items-center gap-2 text-sm font-bold mt-1 ${
                  passwordValidation.valid ? "text-emerald-500" : "text-destructive"
                }`}
              >
                {passwordValidation.valid ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                {passwordValidation.message}
              </motion.div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-lg font-bold text-foreground">
              تأكيد كلمة المرور
            </Label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                placeholder="أعد كتابة كلمة المرور..."
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right ${
                  confirmPassword.length > 0 && (passwordsMatch ? "border-emerald-500/50" : "border-destructive/50")
                }`}
                disabled={registerMutation.isPending}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute inset-y-0 left-3 flex items-center text-muted-foreground hover:text-foreground transition-colors"
              >
                {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
            {confirmPassword.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex items-center gap-2 text-sm font-bold mt-1 ${
                  passwordsMatch ? "text-emerald-500" : "text-destructive"
                }`}
              >
                {passwordsMatch ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                {passwordsMatch ? "كلمتا المرور متطابقتان" : "كلمتا المرور غير متطابقتين"}
              </motion.div>
            )}
          </div>

          <Button
            type="submit"
            disabled={registerMutation.isPending || !isFormValid}
            className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all hover:scale-[1.02]"
          >
            {registerMutation.isPending ? (
              <>
                <Loader2 className="ml-2 h-6 w-6 animate-spin" />
                جاري إنشاء الحساب...
              </>
            ) : (
              <>
                <UserPlus className="ml-2 h-6 w-6" />
                إنشاء الحساب
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}