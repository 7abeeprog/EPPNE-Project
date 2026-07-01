// components/employment/StatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusConfig: Record<string, { label: string; color: string }> = {
  // Job/Application Status
  PENDING: { label: 'قيد الانتظار', color: 'bg-amber-500/20 text-amber-500 border-amber-500/30' },
  REVIEWING: { label: 'قيد المراجعة', color: 'bg-blue-500/20 text-blue-500 border-blue-500/30' },
  APPROVED: { label: 'مقبول', color: 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30' },
  REJECTED: { label: 'مرفوض', color: 'bg-red-500/20 text-red-500 border-red-500/30' },
  
  // Contract Status
  WAITING_SIGNATURE: { label: 'بانتظار التوقيع', color: 'bg-amber-500/20 text-amber-500 border-amber-500/30' },
  PROBATION: { label: 'فترة تجربة', color: 'bg-blue-500/20 text-blue-500 border-blue-500/30' },
  ACTIVE: { label: 'نشط', color: 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30' },
  SUSPENDED: { label: 'موقف', color: 'bg-orange-500/20 text-orange-500 border-orange-500/30' },
  TERMINATED: { label: 'منتهي', color: 'bg-gray-500/20 text-gray-500 border-gray-500/30' },
  
  // Payroll Status
  DRAFT: { label: 'مسودة', color: 'bg-gray-500/20 text-gray-500 border-gray-500/30' },
  PAID: { label: 'مدفوع', color: 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30' },
  
  // Attendance
  PRESENT: { label: 'حاضر', color: 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30' },
  ABSENT: { label: 'غائب', color: 'bg-red-500/20 text-red-500 border-red-500/30' },
  LATE: { label: 'متأخر', color: 'bg-amber-500/20 text-amber-500 border-amber-500/30' },
  HALF_DAY: { label: 'نصف يوم', color: 'bg-blue-500/20 text-blue-500 border-blue-500/30' },
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, color: 'bg-white/5 text-muted-foreground border-white/10' };

  return (
    <span className={cn(
      "text-xs px-2.5 py-1 rounded-full border font-medium",
      config.color,
      className
    )}>
      {config.label}
    </span>
  );
}