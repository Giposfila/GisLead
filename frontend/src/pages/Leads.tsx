import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Campaign, Lead, LeadPage, Message } from "../api/types";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";
import { useJobs } from "../context/JobsContext";
import { ru } from "../i18n/ru";

const t = ru.leads;
const EMPTY_FILTERS = { status: "", websiteStatus: "", hasPhone: "", q: "" };
const errorText = (error: unknown) =>
  error instanceof ApiError ? error.detail : ru.errors.network;

function MessagePanel({
  lead,
  onLeadChanged,
}: {
  lead: Lead;
  onLeadChanged: () => void;
}) {
  const [message, setMessage] = useState<Message | null | undefined>(undefined);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [opening, setOpening] = useState(false);
  const [genJobId, setGenJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { jobs } = useJobs();
  const fetchMessage = useCallback(() => {
    setError(null);
    api
      .get<Message | null>(`/leads/${lead.id}/message`)
      .then((m) => {
        setMessage(m);
        setDraft(m?.text ?? "");
      })
      .catch((err) => {
        setMessage(null);
        setError(errorText(err));
      });
  }, [lead.id]);
  useEffect(fetchMessage, [fetchMessage]);
  useEffect(() => {
    if (!genJobId) return;
    const job = jobs[genJobId];
    if (job?.status === "done") {
      setGenJobId(null);
      setBusy(false);
      fetchMessage();
      onLeadChanged();
    } else if (job?.status === "failed" || job?.status === "cancelled") {
      setGenJobId(null);
      setBusy(false);
      setError(job.detail ?? ru.errors.generic);
    }
  }, [jobs, genJobId, fetchMessage, onLeadChanged]);
  const regenerate = async () => {
    setError(null);
    setBusy(true);
    try {
      const { job_id } = await api.post<{ job_id: string }>(
        `/leads/${lead.id}/generate`,
      );
      setGenJobId(job_id);
    } catch (err) {
      setBusy(false);
      setError(errorText(err));
    }
  };
  const saveDraft = async () => {
    setError(null);
    setSaving(true);
    try {
      setMessage(
        await api.put<Message>(`/leads/${lead.id}/message`, { text: draft }),
      );
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  };
  const openWhatsApp = async () => {
    setError(null);
    setOpening(true);
    // Open during the click so browsers do not block the asynchronous navigation.
    const tab = window.open("about:blank", "_blank");
    if (tab) tab.opener = null;
    try {
      const { url } = await api.get<{ url: string }>(
        `/leads/${lead.id}/wa-link`,
      );
      if (tab) tab.location.href = url;
      else {
        setError(ru.errors.popup);
        return;
      }
      if (window.confirm(t.confirmSent)) {
        await api.patch(`/leads/${lead.id}`, { status: "sent" });
        onLeadChanged();
      }
    } catch (err) {
      tab?.close();
      setError(errorText(err));
    } finally {
      setOpening(false);
    }
  };
  const dirty = !!message && draft !== message.text;
  return (
    <div className="message-panel">
      <label className="field" htmlFor={`message-${lead.id}`}>
        {t.message}
        {message && <span className="field-hint">{message.model}</span>}
      </label>
      {message === undefined && <p role="status">{ru.app.loading}</p>}
      {message === null && !busy && (
        <p className="field-hint">{t.messageEmpty}</p>
      )}
      {busy && (
        <p className="field-hint" role="status">
          {t.generating}
        </p>
      )}
      <textarea
        id={`message-${lead.id}`}
        rows={4}
        value={draft}
        disabled={!message || busy || saving}
        onChange={(e) => setDraft(e.target.value)}
      />
      <div className="message-actions">
        <button
          className="button button-small button-secondary"
          onClick={regenerate}
          disabled={busy || saving || message === undefined}
        >
          <Icon name="spark" size={15} />
          {message ? t.regenerate : t.generate}
        </button>
        <button
          className="button button-small button-secondary"
          onClick={saveDraft}
          disabled={!message || !draft.trim() || !dirty || busy || saving}
        >
          {saving ? ru.settings.saving : ru.common.save}
        </button>
        <button
          className="button button-small button-primary"
          onClick={openWhatsApp}
          disabled={
            !lead.phone_e164 || !message || dirty || busy || saving || opening
          }
        >
          {t.whatsApp}
          <Icon name="arrow" size={15} />
        </button>
      </div>
      {dirty && <p className="field-hint">{t.saveFirst}</p>}
      {error && (
        <p role="alert" className="check-result failure">
          {error}
          <button className="text-link" onClick={fetchMessage}>
            {ru.common.retry}
          </button>
        </p>
      )}
    </div>
  );
}

export default function Leads() {
  const { campaignId } = useParams<{ campaignId?: string }>();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selected, setSelected] = useState(campaignId ?? "");
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [pageNumber, setPageNumber] = useState(1);
  const [page, setPage] = useState<LeadPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);
  const [batchJob, setBatchJob] = useState<string | null>(null);
  const requestId = useRef(0);
  const { jobs } = useJobs();
  const loadCampaigns = () => {
    setError(null);
    api
      .get<Campaign[]>("/campaigns")
      .then(setCampaigns)
      .catch((err) => setError(errorText(err)));
  };
  useEffect(loadCampaigns, []);
  useEffect(() => {
    setSelected(campaignId ?? "");
    setPageNumber(1);
    setExpanded(null);
  }, [campaignId]);
  const fetchLeads = useCallback(() => {
    const id = ++requestId.current;
    if (!selected) {
      setPage(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ page: String(pageNumber) });
    if (filters.status) params.set("status", filters.status);
    if (filters.websiteStatus)
      params.set("website_status", filters.websiteStatus);
    if (filters.hasPhone) params.set("has_phone", filters.hasPhone);
    if (filters.q) params.set("q", filters.q);
    api
      .get<LeadPage>(`/campaigns/${selected}/leads?${params}`)
      .then((result) => {
        if (id === requestId.current) setPage(result);
      })
      .catch((err) => {
        if (id === requestId.current) {
          setPage(null);
          setError(errorText(err));
        }
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false);
      });
  }, [selected, pageNumber, filters]);
  useEffect(fetchLeads, [fetchLeads]);
  useEffect(() => {
    if (
      Object.values(jobs).some(
        (j) =>
          j.campaign_id === Number(selected) &&
          ["done", "failed", "cancelled"].includes(j.status ?? ""),
      )
    )
      fetchLeads();
  }, [jobs, selected, fetchLeads]);
  useEffect(() => {
    if (
      batchJob &&
      ["done", "failed", "cancelled"].includes(jobs[batchJob]?.status ?? "")
    ) {
      setBatchJob(null);
      setGenerating(false);
    }
  }, [jobs, batchJob]);
  const changeFilter = (key: keyof typeof filters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPageNumber(1);
    setExpanded(null);
  };
  const updateStatus = async (lead: Lead, status: string) => {
    try {
      await api.patch(`/leads/${lead.id}`, { status });
      fetchLeads();
    } catch (err) {
      setError(errorText(err));
    }
  };
  const generateAll = async () => {
    if (!window.confirm(t.confirmGenerateAll)) return;
    setGenerating(true);
    setError(null);
    try {
      const { job_id } = await api.post<{ job_id: string }>(
        `/campaigns/${selected}/generate`,
      );
      setBatchJob(job_id);
    } catch (err) {
      setGenerating(false);
      setError(errorText(err));
    }
  };
  const activeCampaign = campaigns.find((c) => String(c.id) === selected);
  const hasLeads =
    activeCampaign &&
    Object.values(activeCampaign.lead_counts).some((count) => count > 0);
  return (
    <div className="page leads-page">
      <PageHeader title={ru.nav.leads} description={t.description}>
        {selected && (
          <button
            className="button button-primary"
            onClick={generateAll}
            disabled={generating || !hasLeads}
          >
            <Icon name="spark" size={17} />
            {generating ? t.generating : t.generateAll}
          </button>
        )}
      </PageHeader>
      <section className="panel">
        <div className="lead-toolbar">
          <label className="campaign-picker">
            <span className="eyebrow">{t.choose}</span>
            <select
              aria-label={t.choose}
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                setPageNumber(1);
                setExpanded(null);
              }}
            >
              {<option value="">{t.choosePlaceholder}</option>}
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} · {c.city}
                </option>
              ))}
            </select>
          </label>
          {activeCampaign && (
            <span className={`badge badge-${activeCampaign.status}`}>
              <i />
              {ru.campaign.statuses[activeCampaign.status]}
            </span>
          )}
        </div>
        {selected && (
          <div className="lead-filters">
            <label className="search-field">
              <Icon name="search" size={17} />
              <input
                aria-label={t.search}
                placeholder={t.search}
                value={filters.q}
                onChange={(e) => changeFilter("q", e.target.value)}
              />
            </label>
            <select
              aria-label={t.website}
              value={filters.websiteStatus}
              onChange={(e) => changeFilter("websiteStatus", e.target.value)}
            >
              <option value="">{t.anyWebsite}</option>
              {Object.entries(t.websiteLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <select
              aria-label={t.phone}
              value={filters.hasPhone}
              onChange={(e) => changeFilter("hasPhone", e.target.value)}
            >
              <option value="">{t.anyPhone}</option>
              <option value="true">{t.withPhone}</option>
              <option value="false">{t.withoutPhone}</option>
            </select>
            <select
              aria-label={t.status}
              value={filters.status}
              onChange={(e) => changeFilter("status", e.target.value)}
            >
              <option value="">{t.anyStatus}</option>
              {Object.entries(t.statuses).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            {Object.values(filters).some(Boolean) && (
              <button
                className="text-link"
                onClick={() => {
                  setFilters(EMPTY_FILTERS);
                  setPageNumber(1);
                }}
              >
                {ru.common.reset}
              </button>
            )}
          </div>
        )}
        {error && (
          <div className="alert alert-error" role="alert">
            {error}
            <button
              className="text-link"
              onClick={() => {
                if (!campaigns.length) loadCampaigns();
                fetchLeads();
              }}
            >
              {ru.common.retry}
            </button>
          </div>
        )}
        {!selected && (
          <div className="empty-state">
            <span className="empty-icon">
              <Icon name="users" size={32} />
            </span>
            <h2>{t.chooseTitle}</h2>
            <p>{t.chooseText}</p>
            <Link to="/campaigns" className="button button-secondary">
              {ru.nav.campaigns}
              <Icon name="arrow" size={16} />
            </Link>
          </div>
        )}
        {selected && loading && (
          <div className="loading-state" role="status">
            <span className="spinner" />
            {ru.app.loading}
          </div>
        )}
        {selected && !loading && page?.items.length === 0 && (
          <div className="empty-state">
            <span className="empty-icon">
              <Icon name="search" size={32} />
            </span>
            <h2>{t.emptyTitle}</h2>
            <p>{t.emptyText}</p>
            <Link to="/campaigns" className="button button-secondary">
              {ru.nav.campaigns}
              <Icon name="arrow" size={16} />
            </Link>
          </div>
        )}
        {selected && !loading && !!page?.items.length && (
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label={ru.nav.leads}
          >
            <table className="data-table leads-table">
              <thead>
                <tr>
                  {[t.company, t.rating, t.phone, t.website, t.status].map(
                    (label) => (
                      <th key={label} scope="col">
                        {label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {page.items.map((lead) => {
                  const isExpanded = expanded === lead.id;
                  return (
                    <Fragment key={lead.id}>
                      <tr className={isExpanded ? "expanded-row" : ""}>
                        <td>
                          <button
                            className="lead-name"
                            aria-expanded={isExpanded}
                            aria-controls={`lead-${lead.id}`}
                            onClick={() =>
                              setExpanded(isExpanded ? null : lead.id)
                            }
                          >
                            <Icon name="chevron" size={15} />
                            {lead.name}
                          </button>
                          <div className="cell-secondary lead-category">
                            {lead.category ?? "—"}
                          </div>
                        </td>
                        <td>
                          <span className="rating">
                            {lead.rating != null ? `★ ${lead.rating}` : "—"}
                          </span>
                          {lead.rating != null && (
                            <div className="cell-secondary">
                              {lead.reviews_count ?? 0}
                            </div>
                          )}
                        </td>
                        <td className="phone-cell">{lead.phone_e164 ?? "—"}</td>
                        <td>
                          <span
                            className={`badge website-${lead.website_status}`}
                          >
                            {t.websiteLabels[lead.website_status]}
                          </span>
                        </td>
                        <td>
                          <span className={`status-text status-${lead.status}`}>
                            {t.statuses[
                              lead.status as keyof typeof t.statuses
                            ] ?? lead.status}
                          </span>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="detail-row">
                          <td colSpan={5}>
                            <div id={`lead-${lead.id}`} className="lead-detail">
                              <div className="lead-contact">
                                <h3>{lead.name}</h3>
                                <dl>
                                  {[
                                    [t.address, lead.address],
                                    [t.website, lead.website],
                                    ["Telegram", lead.telegram_url],
                                    ["Instagram", lead.instagram_url],
                                  ].map(([label, value]) => (
                                    <div key={label}>
                                      <dt>{label}</dt>
                                      <dd>{value ?? "—"}</dd>
                                    </div>
                                  ))}
                                </dl>
                                <label className="field">
                                  {t.status}
                                  <select
                                    value={lead.status}
                                    onChange={(e) =>
                                      updateStatus(lead, e.target.value)
                                    }
                                  >
                                    {Object.entries(t.statuses).map(
                                      ([value, label]) => (
                                        <option key={value} value={value}>
                                          {label}
                                        </option>
                                      ),
                                    )}
                                  </select>
                                </label>
                              </div>
                              <MessagePanel
                                lead={lead}
                                onLeadChanged={fetchLeads}
                              />
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {selected && !loading && page && (
          <div className="panel-footer">
            <span>
              {t.shown}{" "}
              {page.items.length ? (page.page - 1) * page.page_size + 1 : 0}–
              {(page.page - 1) * page.page_size + page.items.length} {t.of}{" "}
              {page.total}
            </span>
            <div className="pagination">
              <button
                className="button button-small button-secondary"
                disabled={pageNumber <= 1}
                onClick={() => {
                  setPageNumber((p) => p - 1);
                  setExpanded(null);
                }}
              >
                {ru.common.previous}
              </button>
              <span>{page.page}</span>
              <button
                className="button button-small button-secondary"
                disabled={page.page * page.page_size >= page.total}
                onClick={() => {
                  setPageNumber((p) => p + 1);
                  setExpanded(null);
                }}
              >
                {ru.common.next}
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
