import { redirect } from "next/navigation";

export default function RootPage() {
  // توجيه عسكري مباشر لأي زائر نحو لوحة التحكم
  // (إذا كان الزائر لا يملك تصريحاً، سيلتقطه الـ proxy ويحوله فوراً لصفحة /login)
  redirect("/dashboard");
}