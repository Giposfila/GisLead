import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Campaign } from "../api/types";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";
import { useJobs } from "../context/JobsContext";
import { ru } from "../i18n/ru";

const EMPTY_FORM = { name: "", niche: "", city: "", source: "twogis_api" };
const totalLeads = (c: Campaign) =>
  Object.values(c.lead_counts).reduce((a, b) => a + b, 0);

export default function Campaigns() {
  const t = ru.campaign;
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [niches, setNiches] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [pending, setPending] = useState<number[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const { jobs } = useJobs();

  const load = () => {
    setError(null);
    api
      .get<Campaign[]>("/campaigns")
      .then(setCampaigns)
      .catch((e) =>
        setError(e instanceof ApiError ? e.detail : ru.errors.network),
      );
  };
  useEffect(() => {
    load();
    api
      .get<string[]>("/niches")
      .then(setNiches)
      .catch(() => setNiches([]));
  }, []);
  useEffect(() => {
    if (
      Object.values(jobs).some((j) =>
        ["done", "failed", "cancelled"].includes(j.status ?? ""),
      )
    )
      load();
  }, [jobs]);
  useEffect(() => {
    if (showForm) dialog.current?.showModal();
    else dialog.current?.close();
  }, [showForm]);

  const createCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await api.post("/campaigns", {
        ...form,
        name: form.name.trim(),
        niche: form.niche.trim(),
        city: form.city.trim(),
      });
      setForm(EMPTY_FORM);
      setShowForm(false);
      load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.detail : ru.errors.generic);
    } finally {
      setSubmitting(false);
    }
  };
  const startCollect = async (id: number) => {
    setError(null);
    setPending((p) => [...p, id]);
    try {
      await api.post(`/campaigns/${id}/collect`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : ru.errors.generic);
    } finally {
      setPending((p) => p.filter((value) => value !== id));
    }
  };
  const visible = campaigns?.filter(
    (c) =>
      (!status || c.status === status) &&
      `${c.name} ${c.niche} ${c.city}`
        .toLocaleLowerCase("ru")
        .includes(query.toLocaleLowerCase("ru")),
  );
  const stats = [
    { label: t.total, value: campaigns?.length ?? 0, icon: "grid" },
    {
      label: t.leads,
      value: campaigns?.reduce((sum, c) => sum + totalLeads(c), 0) ?? 0,
      icon: "users",
    },
    {
      label: t.ready,
      value:
        campaigns?.reduce(
          (sum, c) => sum + (c.lead_counts.message_ready ?? 0),
          0,
        ) ?? 0,
      icon: "spark",
    },
    {
      label: t.clients,
      value:
        campaigns?.reduce((sum, c) => sum + (c.lead_counts.client ?? 0), 0) ??
        0,
      icon: "target",
    },
  ] as const;
  const openForm = () => {
    setFormError(null);
    setShowForm(true);
  };

  return (
    <div className="page">
      <PageHeader title={ru.nav.campaigns} description={t.description}>
        <button className="button button-primary" onClick={openForm}>
          <Icon name="plus" size={18} />
          {t.create}
        </button>
      </PageHeader>
      <div className="stats-strip">
        {stats.map((stat) => (
          <div className="stat" key={stat.label}>
            <div>
              <span>{stat.label}</span>
              <strong>
                {campaigns ? stat.value.toLocaleString("ru") : "—"}
              </strong>
            </div>
            <span className="stat-icon">
              <Icon name={stat.icon} size={21} />
            </span>
          </div>
        ))}
      </div>
      <Link to="/guide" className="onboarding-banner">
        <span className="onboarding-icon">
          <Icon name="book" size={24} />
        </span>
        <div>
          <h2>{t.introTitle}</h2>
          <p>{t.introText}</p>
        </div>
        <span className="onboarding-cta">
          {t.introLink}
          <Icon name="arrow" size={17} />
        </span>
      </Link>
      {error && (
        <div className="alert alert-error" role="alert">
          <span>{error}</span>
          <button className="text-link" onClick={load}>
            {ru.common.retry}
          </button>
        </div>
      )}
      <section className="panel campaign-panel" aria-label={t.listTitle}>
        <div className="panel-heading">
          <h2>
            {t.listTitle}
            <span className="count-badge">{campaigns?.length ?? "—"}</span>
          </h2>
          <label className="search-field">
            <Icon name="search" size={18} />
            <input
              aria-label={t.search}
              placeholder={t.search}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        </div>
        <div className="filter-tabs" role="group" aria-label={t.statusFilter}>
          {[["", ru.common.all], ...Object.entries(t.statuses)].map(
            ([value, label]) => (
              <button
                key={value}
                className={status === value ? "selected" : ""}
                aria-pressed={status === value}
                onClick={() => setStatus(value)}
              >
                {label}
                {value === "collecting" && <span className="tiny-dot" />}
              </button>
            ),
          )}
        </div>
        {!campaigns && !error && (
          <div className="loading-state" role="status">
            <span className="spinner" />
            {ru.app.loading}
          </div>
        )}
        {campaigns && !visible?.length && (
          <div className="empty-state">
            <span className="empty-icon">
              <Icon name={campaigns.length ? "search" : "pin"} size={32} />
            </span>
            <h2>{campaigns.length ? t.noResults : t.emptyTitle}</h2>
            <p>{campaigns.length ? t.noResultsText : t.emptyText}</p>
            {campaigns.length ? (
              <button
                className="button button-secondary"
                onClick={() => {
                  setQuery("");
                  setStatus("");
                }}
              >
                {ru.common.reset}
              </button>
            ) : (
              <button className="button button-primary" onClick={openForm}>
                <Icon name="plus" size={17} />
                {t.create}
              </button>
            )}
          </div>
        )}
        {!!visible?.length && (
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label={ru.nav.campaigns}
          >
            <table className="data-table campaign-table">
              <thead>
                <tr>
                  {t.columns.map((label) => (
                    <th key={label} scope="col">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visible.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <div className="campaign-name">
                        <span className="campaign-avatar">
                          <Icon name="pin" size={20} />
                        </span>
                        <div>
                          <Link to={`/campaigns/${c.id}/leads`}>{c.name}</Link>
                          <div className="cell-secondary">
                            {c.niche}
                            <span>·</span>
                            {c.city}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`badge badge-${c.status}`}>
                        <i />
                        {t.statuses[c.status]}
                      </span>
                    </td>
                    <td>
                      <span className="lead-count">
                        {totalLeads(c).toLocaleString("ru")}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="button button-small button-secondary"
                          disabled={
                            c.status === "collecting" || pending.includes(c.id)
                          }
                          onClick={() => startCollect(c.id)}
                        >
                          <Icon name="play" size={13} />
                          {pending.includes(c.id) ? t.collecting : t.collect}
                        </button>
                        <a
                          className="export-link"
                          href={`/api/campaigns/${c.id}/export?format=csv`}
                          aria-label={`${t.export} CSV · ${c.name}`}
                        >
                          CSV
                        </a>
                        <a
                          className="export-link"
                          href={`/api/campaigns/${c.id}/export?format=xlsx`}
                          aria-label={`${t.export} XLSX · ${c.name}`}
                        >
                          XLSX
                        </a>
                        <Link
                          className="icon-button"
                          to={`/campaigns/${c.id}/leads`}
                          aria-label={`${t.open} · ${c.name}`}
                        >
                          <Icon name="arrow" size={18} />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {campaigns && (
          <div className="panel-footer">
            <span>
              {visible?.length ?? 0} / {campaigns.length} {t.count}
            </span>
            <span>
              <Icon name="shield" size={14} />
              {ru.app.local}
            </span>
          </div>
        )}
      </section>
      <dialog
        ref={dialog}
        className="campaign-dialog"
        aria-labelledby="create-title"
        onCancel={() => setShowForm(false)}
        onClose={() => setShowForm(false)}
        onClick={(e) => {
          if (e.target === e.currentTarget) setShowForm(false);
        }}
      >
        <form onSubmit={createCampaign}>
          <div className="dialog-heading">
            <span className="stat-icon">
              <Icon name="pin" size={24} />
            </span>
            <button
              type="button"
              className="icon-button"
              aria-label={ru.common.close}
              onClick={() => setShowForm(false)}
            >
              <Icon name="close" />
            </button>
          </div>
          <h2 id="create-title">{t.createTitle}</h2>
          <p>{t.createDescription}</p>
          <label className="field">
            {t.name}
            <input
              autoFocus
              required
              maxLength={200}
              value={form.name}
              placeholder={t.namePlaceholder}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <div className="form-columns">
            <label className="field">
              {t.niche}
              <input
                required
                list="niche-catalog"
                value={form.niche}
                placeholder={t.nichePlaceholder}
                onChange={(e) => setForm({ ...form, niche: e.target.value })}
              />
            </label>
            <label className="field">
              {t.city}
              <input
                required
                value={form.city}
                placeholder={t.cityPlaceholder}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
              />
            </label>
          </div>
          <datalist id="niche-catalog">
            {niches.map((n) => (
              <option key={n} value={n} />
            ))}
          </datalist>
          <div className="source-summary">
            <Icon name="globe" />
            <div>
              <strong>{t.sourceName}</strong>
              <small>{t.sourceHint}</small>
            </div>
          </div>
          {formError && (
            <div role="alert" className="alert alert-error">
              {formError}
            </div>
          )}
          <div className="dialog-actions">
            <button
              type="button"
              className="button button-secondary"
              onClick={() => setShowForm(false)}
            >
              {ru.common.cancel}
            </button>
            <button
              className="button button-primary"
              disabled={
                submitting ||
                !form.name.trim() ||
                !form.niche.trim() ||
                !form.city.trim()
              }
            >
              {submitting ? t.creating : t.submit}
              <Icon name="arrow" size={16} />
            </button>
          </div>
        </form>
      </dialog>
    </div>
  );
}
