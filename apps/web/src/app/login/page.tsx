"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import Script from "next/script";
import { Suspense, useRef, useState } from "react";

type ApiFailure = { code: string; message: string };

// Empty locally: no widget, and the API skips the check when APP_ENV=local.
const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? "";

declare global {
  interface Window {
    turnstile?: {
      render(el: HTMLElement, opts: Record<string, unknown>): string;
      reset(id: string): void;
    };
  }
}

async function post(path: string, body: unknown): Promise<ApiFailure | null> {
  try {
    const res = await fetch(`/api/v1${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Baton-Client": "web" },
      body: JSON.stringify(body),
    });
    if (res.ok) return null;
    const data = await res.json().catch(() => null);
    return {
      code: data?.error?.code ?? "unknown",
      message: data?.error?.message ?? "Something went wrong. Please try again.",
    };
  } catch {
    return { code: "offline", message: "You seem to be offline. Check your connection and try again." };
  }
}

function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState(useSearchParams().get("email") ?? "");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [terms, setTerms] = useState(false);
  const [age, setAge] = useState(false);
  const [step, setStep] = useState<"email" | "code" | "details">("email");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [resent, setResent] = useState(false);
  const [token, setToken] = useState("");
  const widgetEl = useRef<HTMLDivElement>(null);
  const widgetId = useRef<string | null>(null);
  const needsCheck = TURNSTILE_SITE_KEY !== "" && token === "";

  function renderWidget() {
    if (!window.turnstile || !widgetEl.current || widgetId.current) return;
    widgetId.current = window.turnstile.render(widgetEl.current, {
      sitekey: TURNSTILE_SITE_KEY,
      callback: setToken,
      "expired-callback": () => setToken(""),
      "error-callback": () => setToken(""),
    });
  }

  async function requestCode(e?: React.SubmitEvent<HTMLFormElement>) {
    e?.preventDefault();
    setPending(true);
    const fail = await post("/auth/request-code", { email, turnstile_token: token });
    // Tokens are single use, so fetch a fresh one for "Send a new code".
    if (widgetId.current) {
      setToken("");
      window.turnstile?.reset(widgetId.current);
    }
    setPending(false);
    setError(fail?.message ?? null);
    if (!fail) setStep("code");
  }

  async function verify(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    const details = step === "details" ? { display_name: name, accept_terms: terms, confirm_age: age } : {};
    const fail = await post("/auth/verify-code", { email, code, ...details });
    setPending(false);
    if (fail?.code === "signup_details_required" && step === "code") {
      setError(null);
      return setStep("details");
    }
    if (fail) return setError(fail.message);
    router.push("/");
    router.refresh();
  }

  const titles = { email: "Welcome to Uniloop.", code: "Check your inbox.", details: "Nice to meet you." };

  return (
    <div className="page">
      <p className="eyebrow">Sign in or join</p>
      <h1 className="display">{titles[step]}</h1>

      {step === "email" && (
        <form className="form" onSubmit={requestCode}>
          <div className="field">
            <label htmlFor="email">College email</label>
            <input id="email" type="email" required autoComplete="email" value={email}
              onChange={(e) => setEmail(e.target.value)} placeholder="you@college.edu" />
            <small>No password to remember or reset. We email you a 6-digit code each time.</small>
          </div>
          {error && <p className="error" role="alert">{error}</p>}
          <div><button className="btn btn-solid" disabled={pending || needsCheck}>{pending ? "Sending…" : "Email me a code"}</button></div>
        </form>
      )}

      {step === "code" && (
        <form className="form" onSubmit={verify}>
          <div className="field">
            <label htmlFor="code">6-digit code sent to {email}</label>
            <input id="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}"
              maxLength={6} required value={code} onChange={(e) => setCode(e.target.value)} />
            <small>The code works once and expires in 10 minutes.</small>
          </div>
          {error && <p className="error" role="alert">{error}</p>}
          <div><button className="btn btn-solid" disabled={pending}>{pending ? "Checking…" : "Sign in"}</button></div>
          <p aria-live="polite">
            Didn&apos;t get it?{" "}
            <button type="button" className="linkish" disabled={pending || needsCheck}
              onClick={async () => { await requestCode(); setResent(true); }}>Send a new code</button>
            {" · "}
            <button type="button" className="linkish" onClick={() => { setStep("email"); setCode(""); }}>Use a different email</button>
            {resent && !error && " · New code sent."}
          </p>
        </form>
      )}

      {step === "details" && (
        <form className="form" onSubmit={verify}>
          <div className="field">
            <label htmlFor="name">Your name</label>
            <input id="name" required maxLength={50} autoComplete="given-name" value={name}
              onChange={(e) => setName(e.target.value)} />
            <small>Shown to buyers and sellers. Example: Asha K.</small>
          </div>
          <label>
            <input type="checkbox" required checked={terms} onChange={(e) => setTerms(e.target.checked)} />{" "}
            I agree to the <Link href="/terms">Terms</Link> and <Link href="/privacy">Privacy Policy</Link>.
          </label>
          <label>
            <input type="checkbox" required checked={age} onChange={(e) => setAge(e.target.checked)} />{" "}
            I am 18 or older.
          </label>
          {error && <p className="error" role="alert">{error}</p>}
          <div><button className="btn btn-solid" disabled={pending}>{pending ? "Joining…" : "Join Uniloop"}</button></div>
        </form>
      )}

      {TURNSTILE_SITE_KEY && (
        <>
          {/* Stays mounted across the email and code steps so one widget serves both. */}
          <div ref={widgetEl} hidden={step === "details"} />
          <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
            onReady={renderWidget} />
        </>
      )}
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
