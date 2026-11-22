import Link from "next/link";
import { ListingGrid } from "@/components/ListingCard";
import { apiGet, type ListingCard } from "@/lib/api";

export const dynamic = "force-dynamic";

const FAQS = [
  ["How do I pay?", "Directly to the seller, in person, when you have the item. Uniloop never handles money, so there are no fees and nothing to refund."],
  ["Who can join?", "Anyone with a verified college email. That's how you know every buyer and seller is from your campus."],
  ["Is it safe to meet?", "Pick a listed pickup point. They're busy, public spots on campus. Check the item before you pay, and report anything that feels off."],
  ["What can't I sell?", "Alcohol, vapes, medicine, weapons, stolen or college property, ID cards, exam papers or paid assignment work, and live animals. See Prohibited Items for the full list."],
  ["How long do listings last?", "60 days. Renew with one tap if it hasn't found a new home yet."],
];

export default async function Home() {
  const feed = await apiGet<{ items: ListingCard[] }>("/listings?limit=8");
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <h1 data-reveal>
            Pass it on.
            <br />
            Campus resale, simplified.
          </h1>
          <p data-reveal>
            Textbooks, calculators, lab coats and cycles from students on your campus. Meet up,
            check it, pay in person.
          </p>
          <div data-reveal>
            <Link href="/search" className="btn">Start browsing</Link>
          </div>
        </div>
        <div className="hero-art" data-reveal aria-hidden="true">
          <div className="box box-2"><b>Notes, Sem 3</b>uniloop.</div>
          <div className="box box-3"><b>₹650</b></div>
          <div className="box box-1">
            <b>Used for one semester is still good for four more.</b>
            uniloop.
          </div>
        </div>
      </section>

      <section id="fresh" className="section">
        <div className="wrap" data-scroll>
          <p className="eyebrow">Fresh on campus</p>
          <h2 className="display">
            Textbooks
            <br />
            Lab gear
            <br />& everything in between
          </h2>
        </div>
        <div data-scroll>
          {feed ? (
            <ListingGrid items={feed.items} />
          ) : (
            <p className="wrap empty">Listings are taking a moment to load. Refresh in a few seconds.</p>
          )}
        </div>
        <p className="wrap more">
          <Link href="/search" className="btn">See everything for sale</Link>
        </p>
      </section>

      <section id="how" className="section wrap split">
        <div className="split-art" data-scroll aria-hidden="true" />
        <div data-scroll>
          <p className="eyebrow">How it works</p>
          <h2 className="display">Snap it, list it, hand it over between classes.</h2>
          <p>
            Add a photo, a price and a pickup point, and you&apos;re live. Buyers message you
            in the app. You meet somewhere public on campus, they check the item, and they pay you
            directly. That&apos;s it.
          </p>
          <Link href="/sell" className="btn">Sell something</Link>
        </div>
      </section>

      <section className="section white">
        <div className="wrap" data-scroll>
          <p className="eyebrow">Keep it simple</p>
          <h2 className="display">
            No fees.
            <br />
            No shipping.
            <br />
            No strangers.
          </h2>
          <p><Link href="/login">Join with your college email</Link></p>
        </div>
      </section>

      <section className="section band">
        <div className="wrap" data-scroll>
          <h2 className="display">
            Every handover keeps a good textbook out of the bin and puts money back in a
            student&apos;s pocket.
          </h2>
          <Link href="/sell">List your first item</Link>
        </div>
      </section>

      <section id="faq" className="section wrap">
        <h2 className="display" data-scroll>FAQs</h2>
        <div className="faq" data-scroll>
          <div>
            {FAQS.map(([q, a], i) => (
              <details key={q} open={i === 0}>
                <summary>{q}</summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
          <p className="note">
            Meet somewhere public on campus. Check the item before you pay. Uniloop does not handle
            payments, so pay only when you have the item.
          </p>
        </div>
      </section>
    </>
  );
}
