// Demo mode (DEMO_DATA=1): serve the bundled fictional catalog instead of calling the API.
// For showcasing without a hosted database. Regenerate demo.json from a seeded local API.
import data from "@/data/demo.json";
import type { Category, ListingCard, ListingDetail } from "./api";

// Keep "2 days ago" fresh: shift every timestamp by the time since export.
const shift = Date.now() - new Date(data.exported_at).getTime();
const moved = (iso: string) => new Date(new Date(iso).getTime() + shift).toISOString();

const listings: ListingCard[] = (data.listings as ListingCard[]).map((l) => ({
  ...l,
  published_at: moved(l.published_at),
}));
const details = data.details as Record<string, ListingDetail>;

function search(params: URLSearchParams) {
  const q = params.get("q")?.toLowerCase().trim();
  const category = params.get("category");
  const sort = params.get("sort") ?? "newest";
  const limit = Number(params.get("limit") ?? 24);
  const offset = Number(params.get("cursor") ?? 0) || 0;

  let items = listings.filter(
    (l) =>
      (!category || l.category_slug === category) &&
      (!q || q.split(/\s+/).every((w) => `${l.title} ${details[l.id]?.description ?? ""}`.toLowerCase().includes(w))),
  );
  if (sort === "price_asc") items = [...items].sort((a, b) => a.price_paise - b.price_paise);
  if (sort === "price_desc") items = [...items].sort((a, b) => b.price_paise - a.price_paise);

  const page = items.slice(offset, offset + limit);
  const next = offset + limit < items.length ? String(offset + limit) : null;
  return { items: page, next_cursor: next };
}

export function demoGet(path: string): unknown {
  const url = new URL(path, "http://demo");
  if (url.pathname === "/catalog/bootstrap") return { categories: data.categories as Category[] };
  if (url.pathname === "/listings") return search(url.searchParams);
  const id = url.pathname.match(/^\/listings\/([^/]+)$/)?.[1];
  if (id && details[id]) {
    const d = details[id];
    return { ...d, published_at: moved(d.published_at), seller_joined: moved(d.seller_joined) };
  }
  return null;
}
