import { Video, Construction } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function LiveSessionsPage() {
    return (
        <div className="container mx-auto py-8 max-w-4xl">
            <div className="flex items-center gap-3 mb-8">
                <Video className="w-8 h-8 text-primary" />
                <div>
                    <h1 className="text-3xl font-bold">الجلسات الحية (Live Sessions)</h1>
                    <p className="text-muted-foreground">إدارة البث المباشر والاجتماعات مع المتدربين</p>
                </div>
            </div>

            <Card className="border-dashed border-2 bg-muted/10">
                <CardHeader className="text-center pb-2">
                    <Construction className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
                    <CardTitle className="text-2xl">مركز البث المباشر قيد التطوير</CardTitle>
                    <CardDescription className="text-lg mt-2">
                        نعمل على ربط هذه الوحدة بنظام المنصة السيادية EPPNE.COM. ستتمكن قريباً من جدولة وإدارة جلساتك الحية من هنا.
                    </CardDescription>
                </CardHeader>
                <CardContent className="text-center pb-8">
                    <p className="text-sm text-muted-foreground">
                        تأكد من متابعة التحديثات القادمة للوحة تحكم المدربين.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}