// proxy.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// ============================================================
// 🔐 قوائم المسارات الموحدة
// ============================================================

// المسارات المحمية (تتطلب توكن صالح)
const PROTECTED_ROUTES = [
  '/dashboard',
  '/wallet',
  '/academy',
  '/academy/*',
  '/commerce',
  '/entities',
  '/marketplace',
  '/settings',
  '/profile',
  '/profile/*',
  '/finance/*',
  '/privacy/*',
];

// المسارات العامة (لا تتطلب توكن، ولكن إذا كان المستخدم مسجلاً يُعاد توجيهه إلى داشبورد)
const PUBLIC_ONLY_ROUTES = [
  '/login',
  '/register',
  '/forgot-password',
  '/verify-email',
];

// ============================================================
// 🚀 منطق الـ Proxy
// ============================================================

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // قراءة التوكن من الكوكيز (أولوية access_token ثم refresh_token)
  const accessToken = request.cookies.get('access_token')?.value;
  const refreshToken = request.cookies.get('refresh_token')?.value;
  const token = accessToken || refreshToken; // استخدام أي توكن متاح

  // التحقق مما إذا كان المسار محمياً
  const isProtected = PROTECTED_ROUTES.some((route) => {
    if (route.endsWith('/*')) {
      const base = route.slice(0, -2);
      return pathname.startsWith(base);
    }
    return pathname.startsWith(route);
  });

  // التحقق مما إذا كان المسار عاماً للمستخدمين غير المسجلين فقط
  const isPublicOnly = PUBLIC_ONLY_ROUTES.some((route) =>
    pathname.startsWith(route)
  );

  // 1️⃣ مستخدم غير مسجل يحاول دخول منطقة محمية → إعادة توجيه إلى تسجيل الدخول
  if (isProtected && !token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 2️⃣ مستخدم مسجل يحاول دخول صفحة عامة (login/register) → إعادة توجيه إلى داشبورد
  if (isPublicOnly && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // 3️⃣ الصفحة الرئيسية (/) → يُسمح للجميع، لكن إذا كان مسجلاً يمكن عرضها، أو توجيه حسب الرغبة
  // (نتركها كما هي، تعرض الصفحة الرئيسية للجميع)

  // 4️⃣ السماح بالمرور لباقي المسارات
  return NextResponse.next();
}

// ============================================================
// ⚙️ تكوين الـ Proxy ليعمل على جميع المسارات باستثناء الثوابت والـ API
// ============================================================

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};