import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
// eppne-web/lib/utils.ts

// أضف هذه الدالة إلى نهاية الملف
export function generateIdempotencyKey(): string {
  return `idemp-${Math.random().toString(36).substr(2, 9)}-${Date.now()}`;
}