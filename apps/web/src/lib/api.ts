// Server-side reads only. No cookies are forwarded, so these return public data (spec 8.1).
const BASE = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

export type ListingCard = {
  id: string;
  title: string;
  price_mode: "fixed" | "negotiable" | "free" | "swap";
  price_paise: number;
  condition: string;
  published_at: string;
  category_slug: string;
  category_name: string;
  pickup_name: string;
  seller_handle: string;
  seller_name: string;
  image?: string;
};

export type ListingDetail = ListingCard & {
  description: string;
  status: "active" | "reserved" | "sold" | "expired" | "draft" | "hidden" | "removed";
  availability_note: string;
  swap_for: string;
  seller_joined: string;
  seller_sold_count: number;
  details: { label: string; value: string | number | boolean }[];
  can_contact: boolean;
  image_credit?: { author: string; license: string; source: string };
};

export type Category = { id: string; slug: string; name: string; icon: string };

export async function apiGet<T>(path: string): Promise<T | null> {
  if (process.env.DEMO_DATA === "1") {
    const { demoGet } = await import("./demo");
    return demoGet(path) as T | null;
  }
  try {
    const res = await fetch(new URL(`/api/v1${path}`, BASE), { cache: "no-store" });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}
