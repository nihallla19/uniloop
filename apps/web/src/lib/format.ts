import type { ListingCard } from "./api";

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export function formatPrice(l: Pick<ListingCard, "price_paise" | "price_mode">): string {
  if (l.price_mode === "free") return "Free";
  if (l.price_mode === "swap") return "Swap";
  const rupees = inr.format(l.price_paise / 100);
  return l.price_mode === "negotiable" ? `${rupees} · Negotiable` : rupees;
}

export const CONDITION: Record<string, { label: string; hint: string }> = {
  new: { label: "New", hint: "Never used" },
  like_new: { label: "Like new", hint: "Used briefly, no visible wear" },
  good: { label: "Good", hint: "Used, works well, minor wear" },
  fair: { label: "Fair", hint: "Visible wear, still works" },
  for_parts: { label: "For parts", hint: "Damaged or not fully working" },
};

// Placeholder artwork per category until photo upload lands.
const ART: Record<string, string> = {
  "books-notes": "art-2",
  electronics: "art-4",
  "calculators-instruments": "art-1",
  "lab-gear-uniforms": "art-3",
  "hostel-room": "art-5",
  "cycles-transport": "art-4",
  "clothing-accessories": "art-1",
  "sports-hobbies": "art-2",
  "tickets-passes": "art-5",
  other: "art-3",
};
export const artFor = (slug: string) => ART[slug] ?? "art-3";

const dateFmt = new Intl.DateTimeFormat("en-IN", { month: "short", year: "numeric", timeZone: "Asia/Kolkata" });
export const monthYear = (iso: string) => dateFmt.format(new Date(iso));

export function timeAgo(iso: string): string {
  const mins = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}
