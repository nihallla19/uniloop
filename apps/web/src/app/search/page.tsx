import Link from "next/link";
import { ListingGrid } from "@/components/ListingCard";
import { apiGet, type Category, type ListingCard } from "@/lib/api";

export const dynamic = "force-dynamic";

const SORTS = [
  ["newest", "Newest"],
  ["price_asc", "Price: low to high"],
  ["price_desc", "Price: high to low"],
] as const;

type Params = { q?: string; category?: string; sort?: string; cursor?: string };

function href(p: Params): string {
  const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v) as [string, string][]);
  return `/search${qs.size ? `?${qs}` : ""}`;
}

export default async function SearchPage({ searchParams }: { searchParams: Promise<Params> }) {
  const { q = "", category = "", sort = "newest", cursor = "" } = await searchParams;
  const query = new URLSearchParams({ limit: "24", sort });
  if (q) query.set("q", q);
  if (category) query.set("category", category);
  if (cursor) query.set("cursor", cursor);

  const [feed, boot] = await Promise.all([
    apiGet<{ items: ListingCard[]; next_cursor: string | null }>(`/listings?${query}`),
    apiGet<{ categories: Category[] }>("/catalog/bootstrap"),
  ]);
  const base = { q, category, sort };

  return (
    <div className="search-page">
      <div className="wrap">
        <p className="eyebrow">Browse</p>
        <h1 className="display">{q ? `Results for “${q}”` : "Everything for sale"}</h1>
        <form className="search-bar" action="/search" role="search">
          <input name="q" defaultValue={q} maxLength={100} aria-label="Search listings"
            placeholder="Try “calculator” or “cycle”" />
          {category && <input type="hidden" name="category" value={category} />}
          <select name="sort" defaultValue={sort} aria-label="Sort" disabled={Boolean(q)}>
            {SORTS.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
          <button className="btn btn-solid">Search</button>
        </form>
        <nav className="chips" aria-label="Categories">
          <Link href={href({ ...base, category: "" })} aria-current={!category ? "page" : undefined}>All</Link>
          {boot?.categories.map((c) => (
            <Link key={c.slug} href={href({ ...base, category: c.slug })}
              aria-current={category === c.slug ? "page" : undefined}>{c.name}</Link>
          ))}
        </nav>
      </div>
      {feed ? <ListingGrid items={feed.items} /> : (
        <p className="wrap empty">Listings are taking a moment to load. Refresh in a few seconds.</p>
      )}
      {feed?.next_cursor && (
        <p className="wrap more">
          <Link className="btn" href={href({ ...base, cursor: feed.next_cursor })}>Show more</Link>
        </p>
      )}
    </div>
  );
}
