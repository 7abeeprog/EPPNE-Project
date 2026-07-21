// components/communications/MailList.tsx
export default function MailList({ items }: { items: any[] }) {
    return (
        <div className="space-y-2">
            {items.length === 0 ? (
                <p className="text-center text-muted-foreground mt-10">لا توجد رسائل حالياً</p>
            ) : (
                items.map((item: any, i: number) => (
                    <div key={i} className="p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-all">
                        <h3 className="font-bold">{item.subject || "بدون عنوان"}</h3>
                        <p className="text-sm text-muted-foreground">{item.snippet || "..."}</p>
                    </div>
                ))
            )}
        </div>
    );
}