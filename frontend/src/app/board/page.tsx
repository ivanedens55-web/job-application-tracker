"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ApplicationCard from "@/components/ApplicationCard";
import ApplicationDialog from "@/components/ApplicationDialog";
import { api, ApiError, clearToken, getToken } from "@/lib/api";
import { STATUSES, type Application, type ApplicationInput, type ApplicationStatus } from "@/lib/types";

const EMPTY_COLUMN_TEXT: Record<ApplicationStatus, string> = {
  Applied: "Applications you've sent show up here.",
  Interview: "Move an application here when you get an interview.",
  Offer: "Offers land here.",
  Rejected: "Closed applications go here.",
};

export default function BoardPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  // undefined = dialog closed, null = adding, Application = editing
  const [editing, setEditing] = useState<Application | null | undefined>(undefined);

  const handleError = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) {
      clearToken();
      router.replace("/login?expired=1");
      return;
    }
    setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
  }, [router]);

  // The backend is the source of truth: after every change, reload the list from it.
  const load = useCallback(async () => {
    try {
      const { items } = await api.listApplications();
      setApplications(items);
      setError("");
    } catch (err) {
      handleError(err);
    }
  }, [handleError]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api.me().then((u) => setEmail(u.email)).catch(handleError);
    load();
  }, [router, load, handleError]);

  async function saveApplication(input: ApplicationInput) {
    // Errors are thrown back to the dialog so it can show them next to the fields.
    if (editing) await api.updateApplication(editing.id, input);
    else await api.createApplication(input);
    setEditing(undefined);
    await load();
  }

  async function changeStatus(app: Application, status: ApplicationStatus) {
    setBusyId(app.id);
    try {
      await api.updateApplication(app.id, { status });
      await load();
    } catch (err) {
      handleError(err);
    } finally {
      setBusyId(null);
    }
  }

  async function deleteApplication(app: Application) {
    if (!window.confirm(`Delete your application to ${app.company}? This can't be undone.`)) return;
    setBusyId(app.id);
    try {
      await api.deleteApplication(app.id);
      await load();
    } catch (err) {
      handleError(err);
    } finally {
      setBusyId(null);
    }
  }

  function logOut() {
    clearToken();
    router.replace("/login");
  }

  // Grouping for display only; every value shown comes from the backend.
  const byStatus = (status: ApplicationStatus) => (applications ?? []).filter((a) => a.status === status);
  const dueCount = (applications ?? []).filter((a) => a.follow_up_due).length;

  return (
    <div className="page">
      <header className="topbar">
        <div className="auth-brand">
          <span className="brand-mark" aria-hidden="true" />
          Job Application Tracker
        </div>
        <div className="topbar-user">
          {email && <span className="topbar-email">{email}</span>}
          <button type="button" className="btn btn-quiet" onClick={logOut}>Log out</button>
        </div>
      </header>

      <main className="board-page">
        <div className="board-head">
          <div>
            <h1>Your applications</h1>
            {applications && (
              <p className="board-summary">
                {applications.length === 0
                  ? "Nothing tracked yet. Add the first job you applied for."
                  : `${applications.length} tracked${dueCount ? `, ${dueCount} waiting on a follow-up` : ""}.`}
              </p>
            )}
          </div>
          <button type="button" className="btn btn-primary" onClick={() => setEditing(null)}>
            Add application
          </button>
        </div>

        {error && (
          <div className="banner" role="alert">
            <span>{error}</span>
            <button type="button" className="btn-text" onClick={load}>Try again</button>
          </div>
        )}

        {applications === null && !error && <p className="loading">Loading your applications…</p>}

        {applications && (
          <div className="board">
            {STATUSES.map((status) => {
              const items = byStatus(status);
              return (
                <section key={status} className={`column column-${status.toLowerCase()}`}
                  aria-labelledby={`col-${status}`}>
                  <h2 id={`col-${status}`} className="column-head">
                    <span>{status}</span>
                    <span className="column-count" aria-label={`${items.length} applications`}>
                      {items.length}
                    </span>
                  </h2>
                  {items.length === 0 ? (
                    <p className="column-empty">{EMPTY_COLUMN_TEXT[status]}</p>
                  ) : (
                    items.map((app) => (
                      <ApplicationCard key={app.id} application={app} busy={busyId === app.id}
                        onStatusChange={(s) => changeStatus(app, s)}
                        onEdit={() => setEditing(app)}
                        onDelete={() => deleteApplication(app)} />
                    ))
                  )}
                </section>
              );
            })}
          </div>
        )}
      </main>

      {editing !== undefined && (
        <ApplicationDialog application={editing} onSave={saveApplication}
          onClose={() => setEditing(undefined)} />
      )}
    </div>
  );
}
