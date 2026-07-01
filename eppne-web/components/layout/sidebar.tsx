// components/layout/sidebar.tsx
"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  // النظام الرئيسي
  LayoutDashboard,
  Wallet,
  Store,
  Building2,
  Settings,
  LogOut,
  ChevronRight,
  // الأكاديمية
  BrainCircuit,
  FileBadge,
  Network,
  GraduationCap,
  Layers,
  PenTool,
  Tent,
  CalendarDays,
  Target,
  Shield,
  ChevronDown,
  BookOpen,
  Trophy,
  UserCheck,
  Building,
  ShieldAlert,
  Cpu,
  ShoppingCart,
  // إضافات
  Users,
  Award,
  Radio,
  FileText,
  BarChart3,
  Home,
  UserCog,
  Activity,
  Clock,
  Zap,
  Sparkles,
  // الخصوصية
  Eye,
  Trash2,
  // المالية
  Coins,
  History,
  // التجارة
  ShoppingBag,
  Package,
  Tag,
  Gift,
  // الإحالة
  Share2,
  Link2,
  DollarSign,
  TrendingUp,
  // SaaS
  Cloud,
  CreditCard,
  LayoutGrid,
} from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { Button } from "@/components/ui/button";

type Role =
  | "STUDENT"
  | "INSTRUCTOR"
  | "ENTERPRISE"
  | "ADMIN"
  | "SUPER_ADMIN"
  | "EXECUTIVE_DIRECTOR";

// ✅ القائمة الكاملة للمنصة (جميع القطاعات)
const menuCategories = [
  // ==========================================
  // 1. النظام الرئيسي (الكل)
  // ==========================================
  {
    category: "النظام الرئيسي",
    icon: LayoutDashboard,
    allowedRoles: [
      "STUDENT",
      "INSTRUCTOR",
      "ENTERPRISE",
      "ADMIN",
      "SUPER_ADMIN",
      "EXECUTIVE_DIRECTOR",
    ],
    items: [
      {
        name: "لوحة التحكم",
        href: "/dashboard",
        icon: LayoutDashboard,
      },
      {
        name: "المحفظة السيادية",
        href: "/finance/wallet",
        icon: Wallet,
      },
    ],
  },

  // ==========================================
  // 2. الأكاديمية السيادية (Academy)
  // ==========================================
  {
    category: "الأكاديمية السيادية",
    icon: GraduationCap,
    allowedRoles: [
      "STUDENT",
      "INSTRUCTOR",
      "ENTERPRISE",
      "ADMIN",
      "SUPER_ADMIN",
      "EXECUTIVE_DIRECTOR",
    ],
    items: [
      {
        name: "المتجر الأكاديمي",
        href: "/academy/store",
        icon: ShoppingCart,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "مقرراتي",
        href: "/academy/my-learning",
        icon: BookOpen,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "لوحة الشرف",
        href: "/academy/leaderboard",
        icon: Trophy,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "مركز الذكاء الاصطناعي",
        href: "/academy/ai-hub",
        icon: BrainCircuit,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "ملفي الأكاديمي",
        href: "/academy/profile",
        icon: UserCog,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "سجل الشهادات",
        href: "/academy/certificates",
        icon: FileBadge,
        roles: ["STUDENT", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "نتائج الاختبارات",
        href: "/academy/quiz-results",
        icon: Award,
        roles: ["STUDENT", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },

  // ==========================================
  // 3. لوحة المدرب (Instructor)
  // ==========================================
  {
    category: "لوحة المدرب",
    icon: UserCheck,
    allowedRoles: ["INSTRUCTOR", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
    items: [
      {
        name: "لوحة المدرب",
        href: "/academy/instructor/dashboard",
        icon: BarChart3,
        roles: ["INSTRUCTOR", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "التقييم والاعتماد",
        href: "/academy/instructor/grading",
        icon: Award,
        roles: ["INSTRUCTOR", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الجلسات الحية",
        href: "/academy/instructor/live-sessions",
        icon: Radio,
        roles: ["INSTRUCTOR", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },

  // ==========================================
  // 4. القيادة الأكاديمية (Admin)
  // ==========================================
  {
    category: "القيادة الأكاديمية",
    icon: Target,
    allowedRoles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
    items: [
      {
        name: "الهيكل التنظيمي",
        href: "/academy/admin/organization",
        icon: Network,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الكيانات التنظيمية",
        href: "/academy/admin/entities",
        icon: Building2,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "إدارة الترسانة",
        href: "/academy/admin/courses",
        icon: Layers,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "استوديو الإبداع",
        href: "/academy/admin/studio",
        icon: PenTool,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "المعسكرات",
        href: "/academy/admin/bootcamps",
        icon: Tent,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الدفعات",
        href: "/academy/admin/cohorts",
        icon: CalendarDays,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "التكليفات",
        href: "/academy/admin/tasks",
        icon: Target,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الجلسات الحية",
        href: "/academy/admin/live-sessions",
        icon: Radio,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "مركز تحكم AI",
        href: "/academy/admin/ai-center",
        icon: Cpu,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "إدارة الشهادات",
        href: "/academy/admin/certificates",
        icon: FileBadge,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "العمليات السيادية",
        href: "/academy/admin/sovereign-ops",
        icon: ShieldAlert,
        roles: ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },

  // ==========================================
  // 5. الخصوصية والأمان (Privacy)
  // ==========================================
  {
    category: "الخصوصية والأمان",
    icon: Shield,
    allowedRoles: [
      "STUDENT",
      "INSTRUCTOR",
      "ENTERPRISE",
      "ADMIN",
      "SUPER_ADMIN",
      "EXECUTIVE_DIRECTOR",
    ],
    items: [
      {
        name: "إعدادات الخصوصية",
        href: "/privacy/settings",
        icon: Eye,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "طلبات المحو",
        href: "/privacy/erasure",
        icon: Trash2,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "إدارة طلبات المحو",
        href: "/privacy/admin/erasure",
        icon: ShieldAlert,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },

  // ==========================================
  // 6. المالية السيادية (Finance)
  // ==========================================
  {
    category: "المالية السيادية",
    icon: Coins,
    allowedRoles: [
      "STUDENT",
      "INSTRUCTOR",
      "ENTERPRISE",
      "ADMIN",
      "SUPER_ADMIN",
      "EXECUTIVE_DIRECTOR",
    ],
    items: [
      {
        name: "محفظتي",
        href: "/finance/wallet",
        icon: Wallet,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "سجل المعاملات",
        href: "/finance/history",
        icon: History,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "إدارة النظام المالي",
        href: "/finance/admin",
        icon: Shield,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },

  // ==========================================
  // 7. التجارة السيادية (Commerce)
  // ==========================================
  {
    category: "التجارة السيادية",
    icon: ShoppingBag,
    allowedRoles: [
      "STUDENT",
      "INSTRUCTOR",
      "ENTERPRISE",
      "ADMIN",
      "SUPER_ADMIN",
      "EXECUTIVE_DIRECTOR",
    ],
    items: [
      {
        name: "المتجر",
        href: "/store",
        icon: Store,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "سلة التسوق",
        href: "/store/cart",
        icon: ShoppingCart,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "طلباتي",
        href: "/store/orders",
        icon: Package,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الإحالة والعمولات",
        href: "/affiliate",
        icon: Share2,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "لوحة تحكم المتجر",
        href: "/store/admin",
        icon: Settings,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },

  // ==========================================
  // 8. نظام الإحالة (Affiliate) - مكرر للتأكيد
  // ==========================================
  {
    category: "نظام الإحالة",
    icon: Gift,
    allowedRoles: [
      "STUDENT",
      "INSTRUCTOR",
      "ENTERPRISE",
      "ADMIN",
      "SUPER_ADMIN",
      "EXECUTIVE_DIRECTOR",
    ],
    items: [
      {
        name: "لوحة التحكم",
        href: "/affiliate",
        icon: LayoutDashboard,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "روابط الدعوة",
        href: "/affiliate/links",
        icon: Link2,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "العمولات",
        href: "/affiliate/commissions",
        icon: DollarSign,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "شجرة الإحالة",
        href: "/affiliate/tree",
        icon: Users,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "سحب العمولات",
        href: "/affiliate/withdraw",
        icon: TrendingUp,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },

  // ==========================================
  // 9. إدارة SaaS (للمشرفين فقط)
  // ==========================================
  {
    category: "إدارة SaaS",
    icon: Cloud,
    allowedRoles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
    items: [
      {
        name: "لوحة التحكم",
        href: "/saas",
        icon: LayoutDashboard,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الخدمات",
        href: "/saas/services",
        icon: Package,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "خطط التسعير",
        href: "/saas/plans",
        icon: LayoutGrid,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الاشتراكات",
        href: "/saas/subscriptions",
        icon: Users,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الفواتير",
        href: "/saas/invoices",
        icon: CreditCard,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الميزات التجريبية",
        href: "/saas/feature-flags",
        icon: Sparkles,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },

  // ==========================================
  // 10. الحساب الشخصي (الكل)
  // ==========================================
  {
    category: "الحساب الشخصي",
    icon: UserCog,
    allowedRoles: [
      "STUDENT",
      "INSTRUCTOR",
      "ENTERPRISE",
      "ADMIN",
      "SUPER_ADMIN",
      "EXECUTIVE_DIRECTOR",
    ],
    items: [
      {
        name: "ملفي الشخصي",
        href: "/profile",
        icon: UserCog,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الجلسات النشطة",
        href: "/profile/sessions",
        icon: Activity,
        roles: ["STUDENT", "INSTRUCTOR", "ENTERPRISE", "ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },

  // ==========================================
  // 11. اللوجستيات والإدارة (مشرفين فقط)
  // ==========================================
  {
    category: "اللوجستيات والإدارة",
    icon: Settings,
    allowedRoles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
    items: [
      {
        name: "الكيانات (Tenants)",
        href: "/entities",
        icon: Building2,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
      {
        name: "الإعدادات العامة",
        href: "/settings",
        icon: Settings,
        roles: ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"],
      },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const userRole = (user?.system_role as Role) || "STUDENT";
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("sidebar-collapsed");
      return saved === "true";
    }
    return false;
  });
  const [openCategories, setOpenCategories] = useState<string[]>([
    "النظام الرئيسي",
    "الأكاديمية السيادية",
  ]);

  useEffect(() => {
    localStorage.setItem("sidebar-collapsed", String(isSidebarCollapsed));
  }, [isSidebarCollapsed]);

  // ✅ تصفية القائمة بناءً على دور المستخدم
  const authorizedCategories = useMemo(() => {
    return menuCategories
      .filter((group) => group.allowedRoles.includes(userRole))
      .map((group) => ({
        ...group,
        items: group.items.filter(
          (item) => !item.roles || item.roles.includes(userRole)
        ),
      }))
      .filter((group) => group.items.length > 0);
  }, [userRole]);

  const toggleCategory = (categoryName: string) => {
    setOpenCategories((prev) =>
      prev.includes(categoryName)
        ? prev.filter((c) => c !== categoryName)
        : [...prev, categoryName]
    );
  };

  return (
    <motion.aside
      initial={{ width: 280 }}
      animate={{ width: isSidebarCollapsed ? 88 : 280 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="relative h-screen bg-card/30 backdrop-blur-2xl border-l border-white/10 flex flex-col shadow-[20px_0_40px_rgba(0,0,0,0.1)] z-50 shrink-0"
    >
      {/* خلفية نيون */}
      <div className="absolute top-0 right-0 w-full h-64 bg-[radial-gradient(ellipse_at_top_right,_rgba(var(--primary-rgb),0.15),_transparent_70%)] pointer-events-none" />

      {/* زر طي القائمة */}
      <Button
        variant="secondary"
        size="icon"
        onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        className="absolute -left-4 top-10 h-8 w-8 rounded-full border border-white/10 shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)] z-50 bg-background/80 backdrop-blur-md hover:bg-primary/20 text-primary transition-all duration-300"
      >
        <motion.div
          animate={{ rotate: isSidebarCollapsed ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          <ChevronRight className="h-4 w-4" />
        </motion.div>
      </Button>

      {/* الشعار */}
      <div className="p-6 flex items-center justify-center min-h-[100px] border-b border-white/5 relative z-10">
        <Link href="/" className="flex items-center gap-3">
          <div className="relative flex items-center justify-center h-12 w-12 rounded-xl bg-primary/10 border border-primary/20 shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)]">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          {!isSidebarCollapsed && (
            <div className="flex flex-col">
              <span className="text-2xl font-black text-foreground drop-shadow-md">
                EPPNE
              </span>
            </div>
          )}
        </Link>
      </div>

      {/* قائمة التنقل */}
      <nav className="flex-1 space-y-4 px-4 py-6 overflow-y-auto custom-scrollbar relative z-10">
        {authorizedCategories.map((group) => {
          const isOpen = openCategories.includes(group.category);
          return (
            <div key={group.category} className="space-y-1.5">
              {!isSidebarCollapsed ? (
                <button
                  onClick={() => toggleCategory(group.category)}
                  className="flex items-center justify-between w-full px-3 py-2.5 rounded-xl text-xs font-bold text-muted-foreground uppercase hover:text-primary transition-all"
                >
                  <span className="flex items-center gap-2">
                    <group.icon className="h-4 w-4" /> {group.category}
                  </span>
                  <ChevronDown
                    className={`h-4 w-4 transition-transform ${
                      isOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>
              ) : (
                <div className="h-px w-8 bg-border/50 mx-auto mb-2" />
              )}

              <AnimatePresence initial={false}>
                {(isOpen || isSidebarCollapsed) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden space-y-1"
                  >
                    {group.items.map((item) => {
                      const isActive =
                        pathname === item.href ||
                        pathname.startsWith(`${item.href}/`);
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={`relative flex items-center ${
                            isSidebarCollapsed ? "justify-center" : "justify-start"
                          } gap-4 px-3 py-3 rounded-xl transition-all ${
                            isActive
                              ? "bg-primary/10 text-primary font-black border border-primary/10"
                              : "text-muted-foreground hover:bg-background/50"
                          }`}
                        >
                          {isActive && (
                            <motion.div
                              layoutId="active-nav"
                              className="absolute right-0 top-1/2 -translate-y-1/2 h-8 w-1.5 bg-primary rounded-l-full"
                            />
                          )}
                          <item.icon className="h-5 w-5" />
                          {!isSidebarCollapsed && (
                            <span className="text-sm">{item.name}</span>
                          )}
                        </Link>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </nav>

      {/* زر تسجيل الخروج */}
      <div className="p-4 border-t border-white/5 relative z-10 bg-background/20 backdrop-blur-md">
        <Button
          variant="ghost"
          onClick={() => logout()}
          className="w-full flex items-center gap-3 h-12 rounded-xl text-muted-foreground hover:text-rose-500"
        >
          <LogOut className="h-5 w-5" />
          {!isSidebarCollapsed && <span className="font-bold">إنهاء الجلسة</span>}
        </Button>
      </div>
    </motion.aside>
  );
}