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
  User,
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
  // القيادة الجديدة
  MessageSquare,
  Workflow,
  Mail,
  Key,
  // الذكاء الاصطناعي
  Bot,
  ShieldCheck,
  Scale,
  // الموارد البشرية
  Briefcase,
  FileCheck, // ✅ تم استبدال License بـ FileCheck
  FileSignature,
  // الصحة
  Heart,
  // النقل
  Truck,
  MapPin,
  Route,
  Ticket,
  // الزراعة
  Sprout,
  // الصناعة
  Factory,
  // السياحة
  Globe,
  // التواصل الاجتماعي
  Users2,
  UserPlus,
  // المناقصات
  Gavel,
  // التأمين
  AlertTriangle,
  // القيادة الاستراتيجية
  Command,
  Bell,
  // الخدمات
  // ✅ تم حذف License من هنا
  // الزمكان
  Brain,
  // إضافية
  Megaphone,
  Warehouse,
  Wrench,
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

// جميع الأدوات المسموح لها (للاستخدام في الفلاتر)
const ALL_ROLES: Role[] = [
  "STUDENT",
  "INSTRUCTOR",
  "ENTERPRISE",
  "ADMIN",
  "SUPER_ADMIN",
  "EXECUTIVE_DIRECTOR",
];
const ADMIN_ROLES: Role[] = ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"];

// ✅ القائمة الكاملة للمنصة (جميع القطاعات) – مرتبة ومنطقية
const menuCategories = [
  // ==========================================
  // 1. النظام الرئيسي (الكل)
  // ==========================================
  {
    category: "النظام الرئيسي",
    icon: LayoutDashboard,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة التحكم",
        href: "/dashboard",
        icon: LayoutDashboard,
        roles: ALL_ROLES,
      },
      {
        name: "المحفظة السيادية",
        href: "/finance/wallet",
        icon: Wallet,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 2. نظام القيادة (الكل)
  // ==========================================
  {
    category: "نظام القيادة",
    icon: Command,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "الاتصالات المركزية",
        href: "/communications/mail/inbox",
        icon: MessageSquare,
        roles: ALL_ROLES,
      },
      {
        name: "الكيانات السيادية",
        href: "/sovereign-entities",
        icon: Building2,
        roles: ALL_ROLES,
      },
      {
        name: "الأتمتة",
        href: "/automation/workflows",
        icon: Workflow,
        roles: ALL_ROLES,
      },
      {
        name: "المشاريع السيادية",
        href: "/projects",
        icon: FileText,
        roles: ALL_ROLES,
      },
      {
        name: "الوكلاء الرقميون",
        href: "/ai-agents",
        icon: Brain,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 3. الأكاديمية السيادية (الكل)
  // ==========================================
  {
    category: "الأكاديمية السيادية",
    icon: GraduationCap,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "المتجر الأكاديمي",
        href: "/academy/store",
        icon: ShoppingCart,
        roles: ALL_ROLES,
      },
      {
        name: "مقرراتي",
        href: "/academy/my-learning",
        icon: BookOpen,
        roles: ALL_ROLES,
      },
      {
        name: "لوحة الشرف",
        href: "/academy/leaderboard",
        icon: Trophy,
        roles: ALL_ROLES,
      },
      {
        name: "مركز الذكاء الاصطناعي",
        href: "/academy/ai-hub",
        icon: BrainCircuit,
        roles: ALL_ROLES,
      },
      {
        name: "ملفي الأكاديمي",
        href: "/academy/profile",
        icon: UserCog,
        roles: ALL_ROLES,
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
  // 4. لوحة المدرب (مدربون + مشرفون)
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
  // 5. القيادة الأكاديمية (مشرفون)
  // ==========================================
  {
    category: "القيادة الأكاديمية",
    icon: Target,
    allowedRoles: ADMIN_ROLES,
    items: [
      {
        name: "الهيكل التنظيمي",
        href: "/academy/admin/organization",
        icon: Network,
        roles: ADMIN_ROLES,
      },
      {
        name: "الكيانات التنظيمية",
        href: "/academy/admin/entities",
        icon: Building2,
        roles: ADMIN_ROLES,
      },
      {
        name: "إدارة الترسانة",
        href: "/academy/admin/courses",
        icon: Layers,
        roles: ADMIN_ROLES,
      },
      {
        name: "استوديو الإبداع",
        href: "/academy/admin/studio",
        icon: PenTool,
        roles: ADMIN_ROLES,
      },
      {
        name: "المعسكرات",
        href: "/academy/admin/bootcamps",
        icon: Tent,
        roles: ADMIN_ROLES,
      },
      {
        name: "الدفعات",
        href: "/academy/admin/cohorts",
        icon: CalendarDays,
        roles: ADMIN_ROLES,
      },
      {
        name: "التكليفات",
        href: "/academy/admin/tasks",
        icon: Target,
        roles: ADMIN_ROLES,
      },
      {
        name: "الجلسات الحية",
        href: "/academy/admin/live-sessions",
        icon: Radio,
        roles: ADMIN_ROLES,
      },
      {
        name: "مركز تحكم AI",
        href: "/academy/admin/ai-center",
        icon: Cpu,
        roles: ADMIN_ROLES,
      },
      {
        name: "إدارة الشهادات",
        href: "/academy/admin/certificates",
        icon: FileBadge,
        roles: ADMIN_ROLES,
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
  // 6. الذكاء الاصطناعي (الكل)
  // ==========================================
  {
    category: "الذكاء الاصطناعي",
    icon: BrainCircuit,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "الوكلاء الرقميون",
        href: "/ai/agents",
        icon: Bot,
        roles: ALL_ROLES,
      },
      {
        name: "الموافقات البشرية",
        href: "/ai/approvals",
        icon: ShieldCheck,
        roles: ALL_ROLES,
      },
      {
        name: "التوأم الرقمي",
        href: "/digital-twin",
        icon: User,
        roles: ALL_ROLES,
      },
      {
        name: "الإرث الرقمي",
        href: "/digital-twin/legacy",
        icon: Clock,
        roles: ALL_ROLES,
      },
      {
        name: "حوكمة الذكاء الاصطناعي",
        href: "/ai-governance",
        icon: Scale,
        roles: ADMIN_ROLES,
      },
    ],
  },

  // ==========================================
  // 7. الخدمات (الكل) - ✅ تم إصلاح الأيقونة هنا
  // ==========================================
  {
    category: "الخدمات",
    icon: ShoppingBag,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "متجر الخدمات",
        href: "/marketplace",
        icon: ShoppingBag,
        roles: ALL_ROLES,
      },
      {
        name: "تراخيصي",
        href: "/marketplace/licenses",
        icon: FileCheck, // ✅ تم التعديل من License إلى FileCheck
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 8. التجارة السيادية (الكل)
  // ==========================================
  {
    category: "التجارة السيادية",
    icon: Store,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "المتجر",
        href: "/store",
        icon: Store,
        roles: ALL_ROLES,
      },
      {
        name: "سلة التسوق",
        href: "/store/cart",
        icon: ShoppingCart,
        roles: ALL_ROLES,
      },
      {
        name: "طلباتي",
        href: "/store/orders",
        icon: Package,
        roles: ALL_ROLES,
      },
      {
        name: "الإحالة والعمولات",
        href: "/affiliate",
        icon: Share2,
        roles: ALL_ROLES,
      },
      {
        name: "لوحة تحكم المتجر",
        href: "/store/admin",
        icon: Settings,
        roles: ADMIN_ROLES,
      },
    ],
  },

  // ==========================================
  // 9. المالية السيادية (الكل)
  // ==========================================
  {
    category: "المالية السيادية",
    icon: Coins,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "المحفظة",
        href: "/finance/wallet",
        icon: Wallet,
        roles: ALL_ROLES,
      },
      {
        name: "سجل المعاملات",
        href: "/finance/history",
        icon: History,
        roles: ALL_ROLES,
      },
      {
        name: "لوحة التحكم (مشرف)",
        href: "/finance/admin",
        icon: Shield,
        roles: ADMIN_ROLES,
      },
    ],
  },

  // ==========================================
  // 10. نظام الإحالة (الكل)
  // ==========================================
  {
    category: "نظام الإحالة",
    icon: Gift,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة التحكم",
        href: "/affiliate",
        icon: LayoutDashboard,
        roles: ALL_ROLES,
      },
      {
        name: "روابط الدعوة",
        href: "/affiliate/links",
        icon: Link2,
        roles: ALL_ROLES,
      },
      {
        name: "العمولات",
        href: "/affiliate/commissions",
        icon: DollarSign,
        roles: ALL_ROLES,
      },
      {
        name: "شجرة الإحالة",
        href: "/affiliate/tree",
        icon: Users,
        roles: ALL_ROLES,
      },
      {
        name: "سحب العمولات",
        href: "/affiliate/withdraw",
        icon: TrendingUp,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 11. إدارة SaaS (مشرفون)
  // ==========================================
  {
    category: "إدارة SaaS",
    icon: Cloud,
    allowedRoles: ADMIN_ROLES,
    items: [
      {
        name: "لوحة التحكم",
        href: "/saas",
        icon: LayoutDashboard,
        roles: ADMIN_ROLES,
      },
      {
        name: "الخدمات",
        href: "/saas/services",
        icon: Package,
        roles: ADMIN_ROLES,
      },
      {
        name: "خطط التسعير",
        href: "/saas/plans",
        icon: LayoutGrid,
        roles: ADMIN_ROLES,
      },
      {
        name: "الاشتراكات",
        href: "/saas/subscriptions",
        icon: Users,
        roles: ADMIN_ROLES,
      },
      {
        name: "الفواتير",
        href: "/saas/invoices",
        icon: CreditCard,
        roles: ADMIN_ROLES,
      },
      {
        name: "الميزات التجريبية",
        href: "/saas/feature-flags",
        icon: Sparkles,
        roles: ADMIN_ROLES,
      },
    ],
  },

  // ==========================================
  // 12. الموارد البشرية (الكل)
  // ==========================================
  {
    category: "الموارد البشرية",
    icon: Users,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "الرئيسية",
        href: "/employment",
        icon: Users,
        roles: ALL_ROLES,
      },
      {
        name: "الوظائف",
        href: "/employment/jobs",
        icon: Briefcase,
        roles: ALL_ROLES,
      },
      {
        name: "طلباتي",
        href: "/employment/applications",
        icon: FileCheck,
        roles: ALL_ROLES,
      },
      {
        name: "عقدي",
        href: "/employment/contracts",
        icon: FileSignature,
        roles: ALL_ROLES,
      },
      {
        name: "الحضور",
        href: "/employment/attendance",
        icon: Clock,
        roles: ALL_ROLES,
      },
      {
        name: "الإجازات",
        href: "/employment/leaves",
        icon: CalendarDays,
        roles: ALL_ROLES,
      },
      {
        name: "الرواتب",
        href: "/employment/payroll",
        icon: DollarSign,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 13. الصحة والطوارئ (الكل)
  // ==========================================
  {
    category: "الصحة والطوارئ",
    icon: Heart,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة التحكم",
        href: "/health",
        icon: Heart,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 14. الأصول والاستثمار (الكل)
  // ==========================================
  {
    category: "الأصول والاستثمار",
    icon: Building2,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "العقارات",
        href: "/realestate",
        icon: Building2,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 15. النقل والمواصلات (الكل)
  // ==========================================
  {
    category: "النقل والمواصلات",
    icon: Truck,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة التحكم",
        href: "/transport",
        icon: LayoutDashboard,
        roles: ALL_ROLES,
      },
      {
        name: "المحطات",
        href: "/transport/hubs",
        icon: MapPin,
        roles: ALL_ROLES,
      },
      {
        name: "الأساطيل",
        href: "/transport/fleets",
        icon: Truck,
        roles: ALL_ROLES,
      },
      {
        name: "المركبات",
        href: "/transport/vehicles",
        icon: Truck,
        roles: ALL_ROLES,
      },
      {
        name: "المسارات",
        href: "/transport/routes",
        icon: Route,
        roles: ALL_ROLES,
      },
      {
        name: "الرحلات",
        href: "/transport/trips",
        icon: Truck,
        roles: ALL_ROLES,
      },
      {
        name: "حجوزاتي",
        href: "/transport/bookings",
        icon: Ticket,
        roles: ALL_ROLES,
      },
      {
        name: "مهام التوصيل",
        href: "/transport/deliveries",
        icon: Package,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 16. الزراعة والأمن الغذائي (الكل)
  // ==========================================
  {
    category: "الزراعة والأمن الغذائي",
    icon: Sprout,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "التكنولوجيا الزراعية",
        href: "/agritech",
        icon: Sprout,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 17. الصناعة والإنتاج (الكل)
  // ==========================================
  {
    category: "الصناعة والإنتاج",
    icon: Factory,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "التصنيع السيادي",
        href: "/manufacturing",
        icon: Factory,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 18. السياحة والرياضة (الكل)
  // ==========================================
  {
    category: "السياحة والرياضة",
    icon: Globe,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة القيادة",
        href: "/tourism-sports",
        icon: Globe,
        roles: ALL_ROLES,
      },
      {
        name: "الوجهات",
        href: "/tourism-sports/destinations",
        icon: Globe,
        roles: ALL_ROLES,
      },
      {
        name: "البرامج",
        href: "/tourism-sports/programs",
        icon: CalendarDays,
        roles: ALL_ROLES,
      },
      {
        name: "الفعاليات",
        href: "/tourism-sports/events",
        icon: Ticket,
        roles: ALL_ROLES,
      },
      {
        name: "تذاكري",
        href: "/tourism-sports/tickets",
        icon: Ticket,
        roles: ALL_ROLES,
      },
      {
        name: "الأندية",
        href: "/tourism-sports/sports/organizations",
        icon: Users,
        roles: ALL_ROLES,
      },
      {
        name: "اللاعبون",
        href: "/tourism-sports/sports/players",
        icon: Users,
        roles: ALL_ROLES,
      },
      {
        name: "الانتقالات",
        href: "/tourism-sports/sports/transfers",
        icon: Users,
        roles: ALL_ROLES,
      },
      {
        name: "البطولات",
        href: "/tourism-sports/sports/tournaments",
        icon: Trophy,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 19. التواصل الاجتماعي (الكل)
  // ==========================================
  {
    category: "التواصل الاجتماعي",
    icon: Users,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة القيادة",
        href: "/social",
        icon: Users,
        roles: ALL_ROLES,
      },
      {
        name: "المنشورات",
        href: "/social/posts",
        icon: FileText,
        roles: ALL_ROLES,
      },
      {
        name: "المجموعات",
        href: "/social/groups",
        icon: Users2,
        roles: ALL_ROLES,
      },
      {
        name: "الصفحات",
        href: "/social/pages",
        icon: UserPlus,
        roles: ALL_ROLES,
      },
      {
        name: "العقود",
        href: "/social/contracts",
        icon: FileSignature,
        roles: ALL_ROLES,
      },
      {
        name: "الفعاليات",
        href: "/social/events",
        icon: Trophy,
        roles: ALL_ROLES,
      },
      {
        name: "المناسبات",
        href: "/social/occasions",
        icon: Heart,
        roles: ALL_ROLES,
      },
      {
        name: "الهدايا",
        href: "/social/gifts",
        icon: Gift,
        roles: ALL_ROLES,
      },
      {
        name: "التوصيات الذكية",
        href: "/social/match",
        icon: Sparkles,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 20. المناقصات والمزايدات (الكل)
  // ==========================================
  {
    category: "المناقصات والمزايدات",
    icon: FileText,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة القيادة",
        href: "/tenders-auctions",
        icon: FileText,
        roles: ALL_ROLES,
      },
      {
        name: "المناقصات",
        href: "/tenders-auctions/tenders",
        icon: FileText,
        roles: ALL_ROLES,
      },
      {
        name: "المزادات",
        href: "/tenders-auctions/auctions",
        icon: Gavel,
        roles: ALL_ROLES,
      },
      {
        name: "عطاءاتي",
        href: "/tenders-auctions/my-bids",
        icon: DollarSign,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 21. التأمين السيادي (الكل)
  // ==========================================
  {
    category: "التأمين السيادي",
    icon: Shield,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة القيادة",
        href: "/insurance",
        icon: Shield,
        roles: ALL_ROLES,
      },
      {
        name: "بوالص التأمين",
        href: "/insurance/policies",
        icon: FileText,
        roles: ALL_ROLES,
      },
      {
        name: "اشتراكاتي",
        href: "/insurance/subscriptions",
        icon: Shield,
        roles: ALL_ROLES,
      },
      {
        name: "مطالباتي",
        href: "/insurance/claims",
        icon: AlertTriangle,
        roles: ALL_ROLES,
      },
      {
        name: "معاشاتي",
        href: "/insurance/pensions",
        icon: DollarSign,
        roles: ALL_ROLES,
      },
      {
        name: "ملف التأمين",
        href: "/insurance/employee-profile",
        icon: User,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 22. التحكيم والنقابات (الكل)
  // ==========================================
  {
    category: "التحكيم والنقابات",
    icon: Scale,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة القيادة",
        href: "/arbitration-syndicates",
        icon: Scale,
        roles: ALL_ROLES,
      },
      {
        name: "قضاياي",
        href: "/arbitration-syndicates/cases",
        icon: Scale,
        roles: ALL_ROLES,
      },
      {
        name: "النقابات",
        href: "/arbitration-syndicates/syndicates",
        icon: Building2,
        roles: ALL_ROLES,
      },
      {
        name: "تراخيصي",
        href: "/arbitration-syndicates/licenses",
        icon: FileCheck, // ✅ تم التعديل هنا أيضاً
        roles: ALL_ROLES,
      },
      {
        name: "الانتخابات",
        href: "/arbitration-syndicates/elections",
        icon: Trophy,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 23. الزمكان (الكل)
  // ==========================================
  {
    category: "الزمكان",
    icon: BrainCircuit,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة القيادة",
        href: "/zamakana",
        icon: BrainCircuit,
        roles: ALL_ROLES,
      },
      {
        name: "عقد المعرفة",
        href: "/zamakana/nodes",
        icon: Network,
        roles: ALL_ROLES,
      },
      {
        name: "الرسم البياني",
        href: "/zamakana/graph",
        icon: Network,
        roles: ALL_ROLES,
      },
      {
        name: "الحملات الكوكبية",
        href: "/zamakana/campaigns",
        icon: Globe,
        roles: ALL_ROLES,
      },
      {
        name: "السيناريوهات",
        href: "/zamakana/scenarios",
        icon: BrainCircuit,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 24. خدمة العملاء والتسويق (الكل)
  // ==========================================
  {
    category: "خدمة العملاء والتسويق",
    icon: Megaphone,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة القيادة",
        href: "/invitations",
        icon: Mail,
        roles: ALL_ROLES,
      },
      {
        name: "العملاء المحتملون",
        href: "/invitations/leads",
        icon: Users,
        roles: ALL_ROLES,
      },
      {
        name: "الحملات التسويقية",
        href: "/invitations/campaigns",
        icon: Megaphone,
        roles: ALL_ROLES,
      },
      {
        name: "الدعوات",
        href: "/invitations/invitations",
        icon: Mail,
        roles: ALL_ROLES,
      },
      {
        name: "تذاكر الدعم",
        href: "/invitations/tickets",
        icon: Ticket,
        roles: ALL_ROLES,
      },
      {
        name: "التحليلات",
        href: "/invitations/analytics",
        icon: BarChart3,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 25. اللوجيستيات والمخازن (الكل)
  // ==========================================
  {
    category: "اللوجيستيات والمخازن",
    icon: Warehouse,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "لوحة القيادة",
        href: "/logistics",
        icon: Warehouse,
        roles: ALL_ROLES,
      },
      {
        name: "المخازن",
        href: "/logistics/warehouses",
        icon: Warehouse,
        roles: ALL_ROLES,
      },
      {
        name: "المخزون",
        href: "/logistics/inventory",
        icon: Package,
        roles: ALL_ROLES,
      },
      {
        name: "المعدات",
        href: "/logistics/equipment",
        icon: Wrench,
        roles: ALL_ROLES,
      },
      {
        name: "التنبؤ",
        href: "/logistics/forecast",
        icon: TrendingUp,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 26. القيادة الاستراتيجية (مشرفون)
  // ==========================================
  {
    category: "القيادة الاستراتيجية",
    icon: Command,
    allowedRoles: ADMIN_ROLES,
    items: [
      {
        name: "لوحة القيادة",
        href: "/command",
        icon: Command,
        roles: ADMIN_ROLES,
      },
      {
        name: "البراندات",
        href: "/command/brands",
        icon: Building2,
        roles: ADMIN_ROLES,
      },
      {
        name: "المستخدمون",
        href: "/command/users",
        icon: Users,
        roles: ADMIN_ROLES,
      },
      {
        name: "التنبيهات",
        href: "/command/alerts",
        icon: Bell,
        roles: ADMIN_ROLES,
      },
      {
        name: "المراقبة",
        href: "/command/monitoring",
        icon: Activity,
        roles: ADMIN_ROLES,
      },
      {
        name: "التقارير",
        href: "/command/reports",
        icon: FileText,
        roles: ADMIN_ROLES,
      },
      {
        name: "الإعدادات",
        href: "/command/settings",
        icon: Settings,
        roles: ADMIN_ROLES,
      },
    ],
  },

  // ==========================================
  // 27. الخصوصية والأمان (الكل)
  // ==========================================
  {
    category: "الخصوصية والأمان",
    icon: Shield,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "إعدادات الخصوصية",
        href: "/privacy/settings",
        icon: Eye,
        roles: ALL_ROLES,
      },
      {
        name: "طلبات المحو",
        href: "/privacy/erasure",
        icon: Trash2,
        roles: ALL_ROLES,
      },
      {
        name: "إدارة طلبات المحو",
        href: "/privacy/admin/erasure",
        icon: ShieldAlert,
        roles: ADMIN_ROLES,
      },
    ],
  },

  // ==========================================
  // 28. الحساب الشخصي (الكل)
  // ==========================================
  {
    category: "الحساب الشخصي",
    icon: UserCog,
    allowedRoles: ALL_ROLES,
    items: [
      {
        name: "ملفي الشخصي",
        href: "/profile",
        icon: UserCog,
        roles: ALL_ROLES,
      },
      {
        name: "الجلسات النشطة",
        href: "/profile/sessions",
        icon: Activity,
        roles: ALL_ROLES,
      },
    ],
  },

  // ==========================================
  // 29. اللوجستيات والإدارة (مشرفون)
  // ==========================================
  {
    category: "اللوجستيات والإدارة",
    icon: Settings,
    allowedRoles: ADMIN_ROLES,
    items: [
      {
        name: "الكيانات (Tenants)",
        href: "/entities",
        icon: Building2,
        roles: ADMIN_ROLES,
      },
      {
        name: "الإعدادات العامة",
        href: "/settings",
        icon: Settings,
        roles: ADMIN_ROLES,
      },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const userRole = (user?.system_role as Role) || "STUDENT";

  // 1. إصلاح حالة الشريط الجانبي (آمن تماماً من انهيار الأزرار)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("sidebar-collapsed");
    if (saved === "true") {
      setIsSidebarCollapsed(true);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("sidebar-collapsed", String(isSidebarCollapsed));
  }, [isSidebarCollapsed]);

  // 2. استرجاع حالة القوائم المفتوحة (التي تم مسحها بالخطأ)
  const [openCategories, setOpenCategories] = useState<string[]>([
    "النظام الرئيسي",
    "الأكاديمية السيادية",
  ]);

  // 3. تصفية القائمة بناءً على الصلاحيات
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

  // 4. دالة فتح وإغلاق القوائم المنسدلة
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
                    className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""
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
                          className={`relative flex items-center ${isSidebarCollapsed ? "justify-center" : "justify-start"
                            } gap-4 px-3 py-3 rounded-xl transition-all ${isActive
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