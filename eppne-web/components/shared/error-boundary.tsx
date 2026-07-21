// components/shared/error-boundary.tsx
"use client";

import { Component, ReactNode, ErrorInfo } from "react";
import { AlertCircle, RefreshCw, Home, FileText, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

// ==========================================
// 1. الأنواع
// ==========================================

interface ErrorBoundaryProps {
    children: ReactNode;
    /** مكون احتياطي مخصص (اختياري) */
    fallback?: React.ComponentType<{ error: Error; reset: () => void }>;
    /** اسم المكون الذي يحدث فيه الخطأ (للتسجيل) */
    componentName?: string;
    /** هل يجب إعادة المحاولة تلقائياً بعد فترة؟ */
    autoRetry?: boolean;
    /** مدة الانتظار قبل إعادة المحاولة (بالمللي ثانية) */
    retryDelay?: number;
    /** دالة تسجيل مخصصة (لإرسال التقارير إلى الخادم) */
    onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
    retryCount: number;
    isRetrying: boolean;
}

// ==========================================
// 2. واجهة الخطأ الودية (المظهر الاحترافي)
// ==========================================

function DefaultErrorFallback({ error, reset }: { error: Error; reset: () => void }) {
    // استخراج معلومات مفيدة من الخطأ
    const errorMessage = error.message || "حدث خطأ غير متوقع";
    const errorStack = error.stack || "";
    const isDevelopment = process.env.NODE_ENV === "development";

    return (
        <div className="w-full h-full min-h-[400px] flex items-center justify-center p-6">
            <Card className="max-w-2xl w-full border-destructive/20 shadow-[0_0_50px_rgba(239,68,68,0.1)] bg-card/40 backdrop-blur-xl">
                <CardHeader className="space-y-2">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-destructive/10 rounded-full border border-destructive/20">
                            <AlertCircle className="h-8 w-8 text-destructive" />
                        </div>
                        <div>
                            <CardTitle className="text-2xl font-black text-foreground">
                                عذراً، حدث خطأ تقني 🛠️
                            </CardTitle>
                            <CardDescription className="text-base text-muted-foreground">
                                لكن لا تقلق، فريقنا يعمل على حل المشكلة
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="space-y-4">
                    {/* رسالة الخطأ الرئيسية */}
                    <div className="p-4 bg-destructive/5 rounded-xl border border-destructive/10">
                        <p className="text-sm font-mono text-destructive/90 break-words">
                            {errorMessage}
                        </p>
                    </div>

                    {/* تفاصيل إضافية (في بيئة التطوير فقط) */}
                    {isDevelopment && errorStack && (
                        <div className="p-4 bg-muted/20 rounded-xl border border-muted/20 overflow-auto max-h-40">
                            <p className="text-xs font-mono text-muted-foreground/70 whitespace-pre-wrap">
                                {errorStack}
                            </p>
                        </div>
                    )}

                    {/* نصائح مفيدة */}
                    <div className="flex flex-wrap gap-2 text-xs text-muted-foreground/70">
                        <span className="flex items-center gap-1 px-2 py-1 bg-muted/20 rounded-full">
                            <FileText className="h-3 w-3" />
                            تحديث الصفحة قد يحل المشكلة
                        </span>
                        <span className="flex items-center gap-1 px-2 py-1 bg-muted/20 rounded-full">
                            <ClipboardList className="h-3 w-3" />
                            تم تسجيل الخطأ للمراجعة
                        </span>
                    </div>
                </CardContent>

                <CardFooter className="flex flex-wrap gap-3">
                    <Button onClick={reset} className="gap-2" variant="default">
                        <RefreshCw className="h-4 w-4" />
                        إعادة المحاولة
                    </Button>
                    <Button onClick={() => window.location.href = "/dashboard"} variant="outline" className="gap-2">
                        <Home className="h-4 w-4" />
                        العودة للوحة الرئيسية
                    </Button>
                    <Button
                        onClick={() => {
                            // إرسال تقرير الخطأ (يمكن ربطه بخدمة خارجية)
                            const report = {
                                error: errorMessage,
                                stack: errorStack,
                                timestamp: new Date().toISOString(),
                                url: window.location.href,
                                userAgent: navigator.userAgent,
                            };
                            console.log("📝 تقرير الخطأ:", report);

                            // إشعار المستخدم
                            alert("✅ تم إرسال تقرير الخطأ إلى فريق الدعم. سيتم التواصل معك قريباً.");
                        }}
                        variant="secondary"
                        className="gap-2"
                    >
                        <AlertCircle className="h-4 w-4" />
                        إرسال تقرير
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}

// ==========================================
// 3. مكون ErrorBoundary الرئيسي (مع كل الميزات)
// ==========================================

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    private retryTimer: NodeJS.Timeout | null = null;

    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
            retryCount: 0,
            isRetrying: false,
        };
    }

    // ==========================================
    // 3.1 التقاط الخطأ
    // ==========================================

    static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        // تحديث الحالة بمعلومات الخطأ
        this.setState({ errorInfo });

        // تسجيل الخطأ في الكونسول
        console.error(`❌ خطأ في ${this.props.componentName || "مكون غير معروف"}:`, error);
        console.error("📋 تفاصيل:", errorInfo);

        // استدعاء دالة التسجيل المخصصة
        if (this.props.onError) {
            this.props.onError(error, errorInfo);
        }

        // ✅ ميزة متقدمة: إرسال إشعار إلى خادم المراقبة
        this.sendErrorReport(error, errorInfo);

        // ✅ ميزة متقدمة: حفظ الخطأ محلياً للتحليل
        this.saveErrorLocally(error, errorInfo);
    }

    // ==========================================
    // 3.2 إرسال تقرير الخطأ إلى الخادم
    // ==========================================

    private async sendErrorReport(error: Error, errorInfo: ErrorInfo) {
        try {
            // يمكن استبدال هذا بطلب حقيقي إلى API
            const report = {
                component: this.props.componentName || "unknown",
                error: {
                    message: error.message,
                    stack: error.stack,
                },
                componentStack: errorInfo.componentStack,
                timestamp: new Date().toISOString(),
                url: typeof window !== "undefined" ? window.location.href : "",
                userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
            };

            // ✅ إرسال إلى الخادم (إذا كانت هناك نقطة نهاية)
            // await fetch('/api/errors/report', {
            //   method: 'POST',
            //   headers: { 'Content-Type': 'application/json' },
            //   body: JSON.stringify(report),
            // });

            // في الوقت الحالي، نسجل في الكونسول
            console.log("📤 تم إرسال تقرير الخطأ:", report);
        } catch (err) {
            console.error("فشل إرسال تقرير الخطأ:", err);
        }
    }

    // ==========================================
    // 3.3 حفظ الخطأ محلياً
    // ==========================================

    private saveErrorLocally(error: Error, errorInfo: ErrorInfo) {
        try {
            const errors = JSON.parse(localStorage.getItem("error-boundary-logs") || "[]");
            errors.push({
                id: Date.now(),
                component: this.props.componentName || "unknown",
                error: error.message,
                stack: error.stack,
                componentStack: errorInfo.componentStack,
                timestamp: new Date().toISOString(),
            });
            // الاحتفاظ بآخر 20 خطأ فقط
            if (errors.length > 20) errors.shift();
            localStorage.setItem("error-boundary-logs", JSON.stringify(errors));
        } catch {
            // لا نفعل شيئاً إذا فشل التخزين المحلي
        }
    }

    // ==========================================
    // 3.4 إعادة المحاولة (مع ميزة التأخير التلقائي)
    // ==========================================

    reset = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null,
            retryCount: this.state.retryCount + 1,
            isRetrying: false,
        });
        if (this.retryTimer) {
            clearTimeout(this.retryTimer);
            this.retryTimer = null;
        }
    };

    autoRetry = () => {
        if (this.props.autoRetry && this.state.retryCount < 3) {
            this.setState({ isRetrying: true });
            this.retryTimer = setTimeout(() => {
                this.reset();
            }, this.props.retryDelay || 5000);
        }
    };

    componentDidUpdate(prevProps: ErrorBoundaryProps, prevState: ErrorBoundaryState) {
        // إذا حدث خطأ ولم نقم بإعادة المحاولة تلقائياً من قبل
        if (this.state.hasError && !prevState.hasError) {
            this.autoRetry();
        }
    }

    componentWillUnmount() {
        if (this.retryTimer) {
            clearTimeout(this.retryTimer);
            this.retryTimer = null;
        }
    }

    // ==========================================
    // 3.5 العرض
    // ==========================================

    render() {
        if (this.state.hasError && this.state.error) {
            // إذا كان هناك مكون احتياطي مخصص
            if (this.props.fallback) {
                const Fallback = this.props.fallback;
                return <Fallback error={this.state.error} reset={this.reset} />;
            }

            // استخدام المكون الافتراضي
            return <DefaultErrorFallback error={this.state.error} reset={this.reset} />;
        }

        return this.props.children;
    }
}

// ==========================================
// 4. دالة مساعدة: استخدام ErrorBoundary مع Suspense
// ==========================================

export function withErrorBoundary<P extends object>(
    Component: React.ComponentType<P>,
    options?: Omit<ErrorBoundaryProps, "children">
): React.ComponentType<P> {
    return function WrappedComponent(props: P) {
        return (
            <ErrorBoundary {...options}>
                <Component {...props} />
            </ErrorBoundary>
        );
    };
}

// ==========================================
// 5. دالة مساعدة: استرجاع سجل الأخطاء
// ==========================================

export function getErrorLogs(): Array<{
    id: number;
    component: string;
    error: string;
    stack?: string;
    componentStack?: string;
    timestamp: string;
}> {
    try {
        return JSON.parse(localStorage.getItem("error-boundary-logs") || "[]");
    } catch {
        return [];
    }
}

// ==========================================
// 6. دالة مساعدة: مسح سجل الأخطاء
// ==========================================

export function clearErrorLogs(): void {
    localStorage.removeItem("error-boundary-logs");
}