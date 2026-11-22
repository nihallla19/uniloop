"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef } from "react";
import { Mark } from "./Logo";

const WORD = "uniloop.";

/** Full-load intro: mark, then the name, then the page slides in from under the curtain. */
export function Preloader() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const el = root.current;
      if (!el) return;
      if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
        el.classList.add("done");
        return;
      }
      const reveal = document.querySelectorAll("[data-reveal]");
      gsap.set(reveal, { autoAlpha: 0, y: 40 });
      gsap
        .timeline({ onComplete: () => el.classList.add("done") })
        .from(".pl-mark", { scale: 0.4, rotate: -135, autoAlpha: 0, duration: 0.9, ease: "expo.out" })
        .from(".pl-letter", { yPercent: 110, duration: 0.7, stagger: 0.06, ease: "expo.out" }, "-=0.35")
        .to(".pl-inner", { y: -30, autoAlpha: 0, duration: 0.45, ease: "power2.in" }, "+=0.45")
        .to(el, { yPercent: -100, duration: 1, ease: "expo.inOut" }, "-=0.1")
        .to(reveal, { autoAlpha: 1, y: 0, duration: 1, stagger: 0.08, ease: "expo.out" }, "-=0.55");
    },
    { scope: root },
  );

  return (
    <div ref={root} className="preloader" aria-hidden="true">
      <div className="pl-inner">
        <Mark className="pl-mark" />
        <span className="pl-word">
          {WORD.split("").map((ch, i) => (
            <span key={i} className="pl-letter">{ch}</span>
          ))}
        </span>
      </div>
    </div>
  );
}
