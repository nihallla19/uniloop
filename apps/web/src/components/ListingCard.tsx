import Link from "next/link";
import type { ListingCard as Listing } from "@/lib/api";
import { CONDITION, artFor, formatPrice, timeAgo } from "@/lib/format";

export function ListingCard({ l }: { l: Listing }) {
  return (
    <Link href={`/listing/${l.id}`} className="card">
      {l.image ? (
        // eslint-disable-next-line @next/next/no-img-element -- static demo files, already sized
        <img className="card-art card-img" src={l.image} alt={l.title} width={800} height={1000} loading="lazy" />
      ) : (
        <div className={`card-art ${artFor(l.category_slug)}`}>{l.category_name}</div>
      )}
      <h3>{l.title}</h3>
      <div className="card-meta">
        <span>{formatPrice(l)}</span>
        <span>{CONDITION[l.condition]?.label}</span>
      </div>
      <div className="card-sub">
        <span className="tag">{l.pickup_name}</span>
        <span>{timeAgo(l.published_at)}</span>
      </div>
    </Link>
  );
}

export function ListingGrid({ items }: { items: Listing[] }) {
  if (items.length === 0) {
    return <p className="wrap empty">Nothing here yet. Try another search or category.</p>;
  }
  return (
    <div className="rail">
      {items.map((l) => <ListingCard key={l.id} l={l} />)}
    </div>
  );
}
