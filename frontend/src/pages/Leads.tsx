import { Fragment, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Campaign, Lead, LeadPage, Message } from "../api/types";
import { useJobs } from "../context/JobsContext";
import { ru } from "../i18n/ru";

const WEBSITE_LABELS: Record<string, { text: string; className: string }> = {
  none: { text: "нет сайта", className: "bg-green-100 text-green-700" },
  alive: { text: "есть сайт", className: "bg-gray-100 text-gray-600" },
  dead: { text: "сайт не работает", className: "bg-yellow-100 text-yellow-700" },
  unknown: { text: "не проверено", className: "bg-gray-100 text-gray-500" },
};

const STATUS_LABELS: Record<string, string> = {
  new: "Новый",
  message_ready: "Сообщение готово",
  sent: "Отправлено",
  replied: "Ответили",
  client: "Клиент",
  rejected: "Отказ",
};

interface Filters {
  status: string;
  websiteStatus: string;
  hasPhone: string;
  q: string;
}

const EMPTY_FILTERS: Filters = { status: "", websiteStatus: "", hasPhone: "", q: "" };

function MessagePanel({ lead, onLeadChanged }: { lead: Lead; onLeadChanged: () => void }) {
  const [message, setMessage] = useState<Message | null | undefined>(undefined);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [genJobId, setGenJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { jobs } = useJobs();

  const fetchMessage = () => {
    api
      .get<Message | null>(`/leads/${lead.id}/message`)
      .then((m) => {
        setMessage(m);
        setDraft(m?.text ?? "");
      })
      .catch(() => setMessage(null));
  };

  useEffect(fetchMessage, [lead.id]);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs, genJobId]);

  const regenerate = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setError(null);
    setBusy(true);
    try {
      const { job_id } = await api.post<{ job_id: string }>(`/leads/${lead.id}/generate`);
      setGenJobId(job_id);
    } catch (err) {
      setBusy(false);
      setError(err instanceof ApiError ? err.detail : ru.errors.generic);
    }
  };

  const saveDraft = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setError(null);
    try {
      const updated = await api.put<Message>(`/leads/${lead.id}/message`, { text: draft });
      setMessage(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : ru.errors.generic);
    }
  };

  const openWhatsApp = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setError(null);
    try {
      const { url } = await api.get<{ url: string }>(`/leads/${lead.id}/wa-link`);
      window.open(url, "_blank", "noreferrer");
      if (window.confirm("Отметить лид как «Отправлено»?")) {
        await api.patch(`/leads/${lead.id}`, { status: "sent" });
        onLeadChanged();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : ru.errors.generic);
    }
  };

  return (
    <div className="mt-2 border-t pt-2">
      <span className="text-gray-500">Сообщение:</span>
      {message === undefined && <p className="text-xs text-gray-400">{ru.app.loading}</p>}
      {message === null && !busy && (
        <p className="text-xs text-gray-400">Ещё не сгенерировано.</p>
      )}
      {busy && <p className="text-xs text-gray-400">Генерация…</p>}
      <textarea
        className="mt-1 w-full rounded border px-2 py-1 text-sm"
        rows={3}
        value={draft}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => setDraft(e.target.value)}
      />
      <div className="mt-2 flex flex-wrap gap-2">
        <button
          className="rounded border px-2 py-1 text-xs disabled:opacity-50"
          onClick={regenerate}
          disabled={busy}
          type="button"
        >
          Сгенерировать заново
        </button>
        <button
          className="rounded border px-2 py-1 text-xs disabled:opacity-50"
          onClick={saveDraft}
          disabled={!draft || draft === message?.text}
          type="button"
        >
          {ru.common.save}
        </button>
        <button
          className="rounded border px-2 py-1 text-xs text-green-700 disabled:opacity-50"
          onClick={openWhatsApp}
          disabled={!lead.phone_e164 || !message}
          type="button"
        >
          Открыть WhatsApp
        </button>
      </div>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export default function Leads() {
  const { campaignId } = useParams<{ campaignId?: string }>();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selected, setSelected] = useState<string>(campaignId ?? "");
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [page, setPage] = useState<LeadPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const { jobs } = useJobs();

  useEffect(() => {
    api.get<Campaign[]>("/campaigns").then(setCampaigns).catch(() => setCampaigns([]));
  }, []);

  const fetchLeads = () => {
    if (!selected) return;
    setError(null);
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.websiteStatus) params.set("website_status", filters.websiteStatus);
    if (filters.hasPhone) params.set("has_phone", filters.hasPhone);
    if (filters.q) params.set("q", filters.q);
    api
      .get<LeadPage>(`/campaigns/${selected}/leads?${params.toString()}`)
      .then(setPage)
      .catch((e: ApiError) => setError(e.detail ?? ru.errors.network));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(fetchLeads, [selected, filters]);

  useEffect(() => {
    if (!selected) return;
    const finished = Object.values(jobs).some(
      (j) => j.campaign_id === Number(selected) && j.status === "done",
    );
    if (finished) fetchLeads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs, selected]);

  const updateStatus = async (lead: Lead, status: string) => {
    try {
      await api.patch(`/leads/${lead.id}`, { status });
      fetchLeads();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : ru.errors.generic);
    }
  };

  return (
    <div className="p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">{ru.nav.leads}</h1>
        <select
          className="rounded border px-2 py-1 text-sm"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          <option value="">Выберите кампанию…</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.niche}, {c.city})
            </option>
          ))}
        </select>

        {selected && (
          <>
            <input
              className="rounded border px-2 py-1 text-sm"
              placeholder="Поиск…"
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            />
            <select
              className="rounded border px-2 py-1 text-sm"
              value={filters.websiteStatus}
              onChange={(e) => setFilters({ ...filters, websiteStatus: e.target.value })}
            >
              <option value="">Сайт: любой</option>
              <option value="none">Нет сайта</option>
              <option value="alive">Есть сайт</option>
              <option value="dead">Сайт не работает</option>
              <option value="unknown">Не проверено</option>
            </select>
            <select
              className="rounded border px-2 py-1 text-sm"
              value={filters.hasPhone}
              onChange={(e) => setFilters({ ...filters, hasPhone: e.target.value })}
            >
              <option value="">Телефон: любой</option>
              <option value="true">С телефоном</option>
              <option value="false">Без телефона</option>
            </select>
            <select
              className="rounded border px-2 py-1 text-sm"
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            >
              <option value="">Статус: любой</option>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </>
        )}
      </div>

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      {!selected && (
        <p className="mt-4 text-sm text-gray-500">Выберите кампанию, чтобы увидеть лиды.</p>
      )}

      {selected && page && page.items.length === 0 && (
        <p className="mt-4 text-sm text-gray-500">
          Лидов не найдено. Запустите сбор на странице «{ru.nav.campaigns}» или измените фильтры.
        </p>
      )}

      {page && page.items.length > 0 && (
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr className="border-b text-gray-500">
              <th className="py-2">Название</th>
              <th>Категория</th>
              <th>Рейтинг</th>
              <th>Телефон</th>
              <th>Сайт</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {page.items.map((lead) => {
              const website = WEBSITE_LABELS[lead.website_status];
              const isExpanded = expanded === lead.id;
              return (
                <Fragment key={lead.id}>
                  <tr
                    className="cursor-pointer border-b hover:bg-gray-50"
                    onClick={() => setExpanded(isExpanded ? null : lead.id)}
                  >
                    <td className="py-2">{lead.name}</td>
                    <td>{lead.category ?? "—"}</td>
                    <td>
                      {lead.rating != null ? `${lead.rating} (${lead.reviews_count ?? 0})` : "—"}
                    </td>
                    <td>{lead.phone_e164 ?? "—"}</td>
                    <td>
                      <span className={`rounded px-2 py-0.5 text-xs ${website.className}`}>
                        {website.text}
                      </span>
                    </td>
                    <td>{STATUS_LABELS[lead.status] ?? lead.status}</td>
                  </tr>
                  {isExpanded && (
                    <tr className="border-b bg-gray-50">
                      <td colSpan={6} className="p-4">
                        <div className="grid max-w-xl gap-2 text-sm">
                          <div>
                            <span className="text-gray-500">Адрес: </span>
                            {lead.address ?? "—"}
                          </div>
                          <div>
                            <span className="text-gray-500">Сайт: </span>
                            {lead.website ?? "—"}
                          </div>
                          <div>
                            <span className="text-gray-500">Telegram: </span>
                            {lead.telegram_url ?? "—"}
                          </div>
                          <div>
                            <span className="text-gray-500">Instagram: </span>
                            {lead.instagram_url ?? "—"}
                          </div>
                          <label className="mt-2 flex items-center gap-2">
                            <span className="text-gray-500">Статус:</span>
                            <select
                              className="rounded border px-2 py-1"
                              value={lead.status}
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) => updateStatus(lead, e.target.value)}
                            >
                              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                                <option key={value} value={value}>
                                  {label}
                                </option>
                              ))}
                            </select>
                          </label>
                          <MessagePanel lead={lead} onLeadChanged={fetchLeads} />
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      )}

      {page && (
        <p className="mt-3 text-xs text-gray-400">
          Показано {page.items.length} из {page.total}
        </p>
      )}
    </div>
  );
}
