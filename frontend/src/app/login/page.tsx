"use client";

import { useEffect, useState } from "react";
import AuthForm from "@/components/AuthForm";

export default function LoginPage() {
  const [notice, setNotice] = useState<string>();
  useEffect(() => {
    // Read the query string in the browser (keeps this page static-friendly).
    if (new URLSearchParams(window.location.search).get("expired")) {
      setNotice("Your session expired. Log in again to continue.");
    }
  }, []);
  return <AuthForm mode="login" notice={notice} />;
}
