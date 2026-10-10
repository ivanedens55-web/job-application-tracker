"use client";

import { formatDate, linkLabel } from "@/lib/format";
import { STATUSES, type Application, type ApplicationStatus } from "@/lib/types";

type Props = {
  application: Application;
  busy: boolean;
  onStatusChange: (status: ApplicationStatus) => void;
  onEdit: () => void;
  onDelete: () => void;
};

export default function ApplicationCard({ application: app, busy, onStatusChange, onEdit, onDelete }: Props) {
  return (
    <article className={`card${app.follow_up_due ? " card-due" : ""}`} aria-busy={busy}>
      <h3 className="card-company">{app.company}</h3>
      <p className="card-role">{app.role}</p>

      {app.follow_up_date && (
        <p className={app.follow_up_due ? "card-followup due" : "card-followup"}>
          {app.follow_up_due ? "Follow up now, due " : "Follow up on "}
          {formatDate(app.follow_up_date)}
        </p>
      )}

      {app.url && (
        // url is validated as http(s) by the backend, so it can't be a javascript: link.
        <a className="card-link" href={app.url} target="_blank" rel="noopener noreferrer">
          {linkLabel(app.url)}
        </a>
      )}

      {app.notes && <p className="card-notes">{app.notes}</p>}

      <div className="card-actions">
        <label className="visually-hidden" htmlFor={`status-${app.id}`}>
          Status for {app.company}
        </label>
        <select id={`status-${app.id}`} value={app.status} disabled={busy}
          onChange={(e) => onStatusChange(e.target.value as ApplicationStatus)}>
          {STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <button type="button" className="btn-text" onClick={onEdit} disabled={busy}>Edit</button>
        <button type="button" className="btn-text danger" onClick={onDelete} disabled={busy}>Delete</button>
      </div>
    </article>
  );
}
