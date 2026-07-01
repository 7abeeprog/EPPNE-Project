// components/auth/LoginForm.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useLogin } from "@/hooks/auth/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, Eye, EyeOff, LogIn } from "lucide-react";
import { toast } from "sonner";

export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const loginMutation = useLogin();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      toast.error("يرجى إدخال اسم المستخدم وكلمة المرور");
      return;
    }
    loginMutation.mutate({ username: username.trim(), password });
  };

  // ✅ معالجة نجاح تسجيل الدخول (Toast مع مدة محددة)
  if (loginMutation.isSuccess) {
    toast.success("مرحباً بعودتك! 🚀", { duration: 3000 });
    router.push("/dashboard");
  }

  return (
    <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.2)] rounded-[2rem] overflow-hidden">
      <CardContent className="p-6 md:p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="username" className="text-lg font-bold text-foreground">
              اسم المستخدم أو البريد الإلكتروني
            </Label>
            <Input
              id="username"
              type="text"
              placeholder="أدخل اسم المستخدم..."
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right"
              disabled={loginMutation.isPending}
              autoComplete="username"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <Label htmlFor="password" className="text-lg font-bold text-foreground">
                كلمة المرور
              </Label>
              <button
                type="button"
                className="text-sm font-bold text-primary hover:underline transition-colors"
              >
                نسيت كلمة المرور؟
              </button>
            </div>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="أدخل كلمة المرور..."
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-inner text-lg rtl:text-right"
                disabled={loginMutation.isPending}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 left-3 flex items-center text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            disabled={loginMutation.isPending || !username.trim() || !password.trim()}
            className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all hover:scale-[1.02]"
          >
            {loginMutation.isPending ? (
              <>
                <Loader2 className="ml-2 h-6 w-6 animate-spin" />
                جاري تسجيل الدخول...
              </>
            ) : (
              <>
                <LogIn className="ml-2 h-6 w-6" />
                دخول
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}