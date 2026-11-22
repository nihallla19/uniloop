import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { apiGet, type ListingDetail } from "@/lib/api";
import { CONDITION, artFor, formatPrice, monthYear, timeAgo } from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ id: string }> };

const STATE_LABEL: Partial<Record<ListingDetail["status"], string>> = {
  reserved: "Reserved",
  sold: "This one has been passed on.",
  expired: "This listing has expired.",
};

async function load(id: string) {
  const l = await apiGet<ListingDetail>(`/listings/${encodeURIComponent(id)}`);
  if (!l) notFound();
  return l;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const l = await apiGet<ListingDetail>(`/listings/${encodeURIComponent((await params).id)}`);
  return l ? { title: `${l.title} · Uniloop`, description: l.description.slice(0, 150) } : {};
}

export default async function ListingPage({ params }: Props) {
  const l = await load((await params).id);
  const condition = CONDITION[l.condition];
  const state = STATE_LABEL[l.status];

  return (
    <article className="detail wrap">
      {l.image ? (
        <figure className="detail-art detail-figure">
          {/* eslint-disable-next-line @next/next/no-img-element -- static demo files, already sized */}
          <img src={l.image} alt={l.title} width={800} height={1000} />
          {l.image_credit && (
            <figcaption>
              Photo: <a href={l.image_credit.source} rel="noopener noreferrer" target="_blank">{l.image_credit.author}</a>, {l.image_credit.license}
            </figcaption>
          )}
        </figure>
      ) : (
        <div className={`detail-art ${artFor(l.category_slug)}`} role="img" aria-label={`${l.category_name}: ${l.title}`}>
          {l.category_name}
        </div>
      )}
      <div className="detail-body">
        <p className="eyebrow"><Link href={`/search?category=${l.category_slug}`}>{l.category_name}</Link> · {timeAgo(l.published_at)}</p>
        <h1 className="display">{l.title}</h1>
        <p className="detail-price">{formatPrice(l)}</p>
        {state && <p className="note">{state}</p>}

        <dl className="facts">
          <div><dt>Condition</dt><dd>{condition?.label} <small>({condition?.hint})</small></dd></div>
          <div><dt>Pickup</dt><dd>{l.pickup_name}</dd></div>
          {l.availability_note && <div><dt>Available</dt><dd>{l.availability_note}</dd></div>}
          {l.swap_for && <div><dt>Swap for</dt><dd>{l.swap_for}</dd></div>}
          {l.details.map((d) => (
            <div key={d.label}><dt>{d.label}</dt><dd>{typeof d.value === "boolean" ? (d.value ? "Yes" : "No") : d.value}</dd></div>
          ))}
        </dl>

        {l.description && <p className="detail-desc">{l.description}</p>}

        {l.can_contact && <Link href="/login" className="btn btn-solid">Message seller</Link>}

        <div className="seller">
          <div className="avatar" aria-hidden="true">{l.seller_name.charAt(0)}</div>
          <div>
            <strong>{l.seller_name}</strong>
            <span>@{l.seller_handle} · Joined {monthYear(l.seller_joined)} · {l.seller_sold_count} sold</span>
          </div>
        </div>
        <p className="note">Meet somewhere public on campus. Check the item before you pay. Uniloop does not handle payments.</p>
      </div>
    </article>
  );
}
