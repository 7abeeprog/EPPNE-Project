// app/(dashboard)/social/events/page.tsx
'use client';

import { useState } from 'react';
import { useEvents } from '@/hooks/social/useEvents';
import EventCard from '@/components/social/EventCard';
import { Loader2, Plus, Calendar } from 'lucide-react';
import Link from 'next/link';

export default function EventsPage() {
  const { data: events, isLoading } = useEvents();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground/90">📅 الفعاليات الاجتماعية</h1>
        <Link
          href="/social/events/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          فعالية جديدة
        </Link>
      </div>

      {events?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Calendar className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد فعاليات</p>
          <p className="text-sm">نظم فعاليتك الأولى</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {events?.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}