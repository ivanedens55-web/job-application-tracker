"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { STATUSES, type Application, type ApplicationInput, type ApplicationStatus } from "@/lib/types";

type Props = {
  application: Application | null; // null = adding a new one
  onSave: (input: ApplicationInput) => Promise<void>;
  onClose: () => void;
};

function toForm(app: Application | null) {
  return {
    company: app?.company ?? "",
    role: app?.role ?? "",
    url: app?.url ?? "",
    status: app?.status ?? ("Applied" as ApplicationStatus),
    follow_up_date: app?.follow_up_date ?? "",
    notes: app?.notes ?? "",
  };
}

export default function ApplicationDialog({ application, onSave, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [form, setForm] = useState(() => toForm(application));
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const isNew = application === null;

  useEffect(() => {
    dialogRef.current?.showModal(); // Native modal: focus trap and Esc to close for free.
  }, []);

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setFieldErrors({});
    try {
      // Empty optional fields are sent as null; the backend validates everything.
      await onSave({
        company: form.company,
        role: form.role,
        url: form.url.trim() || null,
        status: form.status,
        follow_up_date: form.follow_up_date || null,
        notes: form.notes.trim() || null,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        setFieldErrors(Object.fromEntries(err.details.map((d) => [d.field, d.message])));
      } else {
        setError("Something went wrong. Please try again.");
      }
      setBusy(false);
    }
  }

  const fieldError = (name: string) =>
    fieldErrors[name] && <span className="field-error">{fieldErrors[name]}</span>;

  return (
    <dialog ref={dialogRef} className="dialog" onClose={onClose} aria-labelledby="dialog-title">
      <form onSubmit={handleSubmit} noValidate>
        <h2 id="dialog-title">{isNew ? "Add application" : `Edit ${application.company}`}</h2>

        <div className="field-row">
          <label>
            Company
            <input required maxLength={120} value={form.company} autoFocus
              onChange={(e) => update("company", e.target.value)} />
            {fieldError("company")}
          </label>
          <label>
            Role
            <input required maxLength={120} value={form.role}
              onChange={(e) => update("role", e.target.value)} />
            {fieldError("role")}
          </label>
        </div>

        <label>
          <span>Link to the job posting <span className="optional">(optional)</span></span>
          <input type="url" maxLength={2048} placeholder="https://" value={form.url}
            onChange={(e) => update("url", e.target.value)} />
          {fieldError("url")}
        </label>

        <div className="field-row">
          <label>
            Status
            <select value={form.status} onChange={(e) => update("status", e.target.value)}>
              {STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
            {fieldError("status")}
          </label>
          <label>
            <span>Follow up on <span className="optional">(optional)</span></span>
            <input type="date" value={form.follow_up_date}
              onChange={(e) => update("follow_up_date", e.target.value)} />
            {fieldError("follow_up_date")}
          </label>
        </div>

        <label>
          <span>Notes <span className="optional">(optional)</span></span>
          <textarea rows={3} maxLength={2000} value={form.notes}
            onChange={(e) => update("notes", e.target.value)} />
          {fieldError("notes")}
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}

        <div className="dialog-actions">
          <button type="button" className="btn btn-quiet" onClick={() => dialogRef.current?.close()}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Saving…" : isNew ? "Add application" : "Save changes"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
