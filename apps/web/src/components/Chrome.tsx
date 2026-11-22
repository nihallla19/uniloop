"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Mark } from "./Logo";

const icon = { fill: "none", stroke: "currentColor", strokeWidth: 1.6, viewBox: "0 0 24 24" } as const;

export function Header() {
  // Light-on-dark only while over the home hero.
  const isHome = usePathname() === "/";
  const [pastHero, setPastHero] = useState(false);
  useEffect(() => {
    const onScroll = () => setPastHero(window.scrollY > window.innerHeight * 0.85);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  const onLight = !isHome || pastHero;
  return (
    <header className={`header${onLight ? " on-light" : ""}`}>
      <Link href="/" className="brand" aria-label="Uniloop home">
        <Mark /> uniloop.
      </Link>
      <nav className="nav" aria-label="Main">
        <Link href="/search">Browse</Link>
        <Link href="/sell">Sell</Link>
        <Link href="/#how">How it works</Link>
        <Link href="/#faq">Safety</Link>
      </nav>
      <div className="icons">
        <Link href="/search" aria-label="Search">
          <svg {...icon}><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
        </Link>
        <Link href="/login" aria-label="Sign in">
          <svg {...icon}><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></svg>
        </Link>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <div>
        <h4>Got something to pass on?</h4>
        <p>List it in under a minute with your college email.</p>
        <form className="pill-input" action="/login">
          <input name="email" aria-label="College email" type="email" placeholder="College email" />
          <button aria-label="Continue">→</button>
        </form>
      </div>
      <div>
        <h4>No money through us</h4>
        <p>Uniloop does not handle payments. Meet somewhere public on campus and pay only when you have the item.</p>
      </div>
      <div>
        <h4>Helpful links</h4>
        <ul>
          <li><Link href="/terms">Terms</Link></li>
          <li><Link href="/privacy">Privacy Policy</Link></li>
          <li><Link href="/safety">Safety Tips</Link></li>
          <li><Link href="/prohibited">Prohibited Items</Link></li>
        </ul>
      </div>
      <div>
        <h4>Quick links</h4>
        <ul>
          <li><Link href="/search">Browse</Link></li>
          <li><Link href="/sell">Sell</Link></li>
          <li><Link href="/login">Sign in</Link></li>
          <li><Link href="/contact">Contact</Link></li>
        </ul>
      </div>
    </footer>
  );
}
