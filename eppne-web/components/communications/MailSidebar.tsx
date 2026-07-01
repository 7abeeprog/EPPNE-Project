// components/communications/MailSidebar.tsx
'use client';
import Link from 'next/link';
import { Inbox, Send, Trash2, Archive, Star } from 'lucide-react';
import { cn } from '@/lib/utils';

const items = [
  { label: 'الوارد', icon: Inbox, href: '/communications/mail/inbox' },
  { label: 'المرسلات', icon: Send, href: '/communications/mail/sent' },
  { label: 'المهمة', icon: Star, href: '/communications/mail/starred' },
  { label: 'الأرشيف', icon: Archive, href: '/communications/mail/archive' },
  { label: 'سلة المحذوفات', icon: Trash2, href: '/communications/mail/trash' },
];

export default function MailSidebar({ active }: { active: string }) {
  return <div className="w-56 shrink-0 space-y-2 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 h-fit">
    <Link href="/communications/mail/compose" className="flex items-center justify-center w-full py-2 px-4 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300">✏️ بريد جديد</Link>
    <div className="h-px bg-white/10 my-2" />
    {items.map((item) => <Link key={item.href} href={item.href} className={cn("flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-200 text-sm", active === item.href.split('/').pop() ? "bg-primary/20 text-primary shadow-[0_0_20px_rgba(var(--primary-rgb),0.1)]" : "hover:bg-white/5 text-muted-foreground")}><item.icon className="w-4 h-4" />{item.label}</Link>)}
  </div>;
}