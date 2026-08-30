// eppne-web/lib/format.ts

/**
 * Decimal fields from the backend (Pydantic `Decimal`/`condecimal`) are
 * serialized as JSON strings to preserve exact precision — never treat
 * them as `number`. This formats them for display only; it never computes
 * an amount that gets sent back to the backend (see: "Never trust
 * client-computed amounts").
 *
 * Intl.NumberFormat.format() accepts a numeric string directly and
 * preserves full arbitrary-precision (ECMA-402 NumberFormat v3) instead of
 * first coercing through a JS `number` (float64), which silently loses
 * precision for values with more significant digits than float64 can
 * hold. Verified live on this project's Node runtime — see
 * .claude/reports/frontend-decimal-standard-convention-session-log.md §4.1.
 */
export function formatDecimalString(
  value: string | null | undefined,
  options: Intl.NumberFormatOptions = { minimumFractionDigits: 2, maximumFractionDigits: 2 }
): string {
  if (value === null || value === undefined || value === '') return '—';
  if (!/^-?\d+(\.\d+)?$/.test(value)) return '—';
  return new Intl.NumberFormat('en-US', options).format(value as unknown as number);
}
