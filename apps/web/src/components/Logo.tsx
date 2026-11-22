/** Baton mark: a relay baton mid-handoff, with motion trails. */
export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <rect x="20" y="3" width="9" height="30" rx="4.5" transform="rotate(40 24.5 18)" fill="currentColor" />
      <path d="M3 22h8M6 28h7M10 34h6" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}
