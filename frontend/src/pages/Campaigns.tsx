import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Campaign } from "../api/types";
import { ru } from "../i18n/ru";

const STATUS_LABELS: Record<Campaign["status"], string> = {
  draft: "Черновик",
  collecting: "Сбор данных…",
  ready: "Готово",
  failed: "Ошибка",
};

const STATUS_CLASSES: Record<Campaign["status"], string> = {
  draft: "bg-gray-100 text-gray-700",
  collecting: "bg-blue-100 text-blue-700",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

interface NewCampaignForm {
  name: string;
  niche: string;
  city: string;
  source: string;
}

const EMPTY_FORM: NewCampaignForm = { name: "", niche: "", city: "", source: "twogis_api" };

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [niches, setNiches] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<NewCampaignForm>(EMPTY_FORM);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    api
      .get<Campaign[]>("/campaigns")
      .then(setCampaigns)
      .catch((e: ApiError) => setError(e.detail ?? ru.errors.network));
  };

  useEffect(() => {
    load();
    api.get<string[]>("/niches").then(setNiches).catch(() => setNiches([]));
  }, []);

  const createCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/campaigns", form);
      setForm(EMPTY_FORM);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : ru.errors.generic);
    } finally {
      setSubmitting(false);
    }
  };

  const startCollect = async (id: number) => {
    try {
      await api.post(`/campaigns/${id}/collect`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : ru.errors.generic);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{ru.nav.campaigns}</h1>
        <button
          className="rounded bg-gray-900 px-3 py-1.5 text-sm text-white"
          onClick={() => setShowForm((v) => !v)}
          type="button"
        >
          Новая кампания
        </button>
      </div>

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      {showForm && (
        <form onSubmit={createCampaign} className="mt-4 grid max-w-md gap-3 rounded border p-4">
          <input
            className="rounded border px-2 py-1 text-sm"
            placeholder="Название кампании"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            className="rounded border px-2 py-1 text-sm"
            placeholder="Ниша (например, веб-студия)"
            required
            list="niche-catalog"
            value={form.niche}
            onChange={(e) => setForm({ ...form, niche: e.target.value })}
          />
          <datalist id="niche-catalog">
            {niches.map((n) => (
              <option key={n} value={n} />
            ))}
          </datalist>
          <input
            className="rounded border px-2 py-1 text-sm"
            placeholder="Город"
            required
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
          />
          <button
            className="rounded bg-gray-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
            disabled={submitting}
            type="submit"
          >
            Создать
          </button>
        </form>
      )}

      {!campaigns && !error && <p className="mt-4 text-sm text-gray-500">{ru.app.loading}</p>}

      {campaigns && campaigns.length === 0 && (
        <p className="mt-4 text-sm text-gray-500">Кампаний пока нет — создайте первую.</p>
      )}

      {campaigns && campaigns.length > 0 && (
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr className="border-b text-gray-500">
              <th className="py-2">Название</th>
              <th>Ниша / Город</th>
              <th>Статус</th>
              <th>Лиды</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id} className="border-b">
                <td className="py-2">
                  <Link className="hover:underline" to={`/campaigns/${c.id}/leads`}>
                    {c.name}
                  </Link>
                </td>
                <td>
                  {c.niche} / {c.city}
                </td>
                <td>
                  <span className={`rounded px-2 py-0.5 text-xs ${STATUS_CLASSES[c.status]}`}>
                    {STATUS_LABELS[c.status]}
                  </span>
                </td>
                <td>{Object.values(c.lead_counts).reduce((a, b) => a + b, 0)}</td>
                <td className="flex flex-wrap items-center gap-3 py-2">
                  <button
                    className="text-xs text-blue-700 hover:underline disabled:text-gray-400"
                    disabled={c.status === "collecting"}
                    onClick={() => startCollect(c.id)}
                    type="button"
                  >
                    Собрать лиды
                  </button>
                  <a
                    className="text-xs text-gray-500 hover:underline"
                    href={`/api/campaigns/${c.id}/export?format=csv`}
                  >
                    CSV
                  </a>
                  <a
                    className="text-xs text-gray-500 hover:underline"
                    href={`/api/campaigns/${c.id}/export?format=xlsx`}
                  >
                    XLSX
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
