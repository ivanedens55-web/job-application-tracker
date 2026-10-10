"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError, setToken } from "@/lib/api";

type Mode = "login" | "register";

const COPY = {
  login: { title: "Log in", button: "Log in", busy: "Logging in…", switchText: "No account yet?", switchLink: "Create one", switchHref: "/register" },
  register: { title: "Create your account", button: "Create account", busy: "Creating account…", switchText: "Already have an account?", switchLink: "Log in", switchHref: "/login" },
};

export default function AuthForm({ mode, notice }: { mode: Mode; notice?: string }) {
  const router = useRouter();
  const copy = COPY[mode];
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") await api.register(email, password);
      const token = await api.login(email, password);
      setToken(token.access_token);
      router.replace("/board");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setBusy(false);
    }
  }

  return (
    <main className="auth">
      <div className="auth-brand">
        <span className="brand-mark" aria-hidden="true" />
        Job Application Tracker
      </div>
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1>{copy.title}</h1>
        {notice && <p className="notice">{notice}</p>}
        <label>
          Email
          <input type="email" autoComplete="email" required maxLength={254}
            value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" required minLength={8} maxLength={128}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password} onChange={(e) => setPassword(e.target.value)} />
          {mode === "register" && <span className="hint">At least 8 characters.</span>}
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? copy.busy : copy.button}
        </button>
        <p className="switch">
          {copy.switchText} <Link href={copy.switchHref}>{copy.switchLink}</Link>
        </p>
      </form>
    </main>
  );
}
