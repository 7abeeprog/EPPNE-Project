// app/(dashboard)/tourism-sports/destinations/page.tsx
'use client';

import { useDestinations } from '@/hooks/tourism-sports/useDestinations';
import DestinationCard from '@/components/tourism-sports/DestinationCard';
import { Loader2, Plus } from 'lucide-react';
import Link from 'next/link';

export default function DestinationsPage() {
  const { data: destinations, isLoading } = useDestinations();

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
        <h1 className="text-2xl font-bold text-foreground/90">🌍 الوجهات السياحية</h1>
        <Link
          href="/tourism-sports/destinations/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          وجهة جديدة
        </Link>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {destinations?.map((dest) => (
          <DestinationCard key={dest.id} destination={dest} />
        ))}
      </div>
    </div>
  );
}