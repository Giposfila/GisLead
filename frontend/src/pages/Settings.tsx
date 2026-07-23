import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { ru } from "../i18n/ru";

interface SettingsOut {
  app: { host: string; port: number; open_browser: boolean; auth_token_is_set: boolean };
  source: {
    active: string;
    twogis_api_key_is_set: boolean;
    scraper_enabled: boolean;
    scraper_max_orgs: number;
  };
  llm: {
    provider: string;
    base_url: string;
    api_key_is_set: boolean;
    model: string;
    concurrency: number;
  };
  limits: { twogis_rps: number; website_check_concurrency: number };
  outreach: { user_offer: string; extra_instructions: string; template: string };
}

interface HealthCheck {
  ok: boolean;
  detail: string;
}

const LLM_PRESETS: { label: string; provider: string; base_url: string }[] = [
  { label: "Ollama (локально)", provider: "openai_compat", base_url: "http://localhost:11434/v1" },
  { label: "OpenAI", provider: "openai_compat", base_url: "https://api.openai.com/v1" },
  { label: "OpenRouter", provider: "openai_compat", base_url: "https://openrouter.ai/api/v1" },
  { label: "Anthropic", provider: "anthropic", base_url: "" },
];

export default function Settings() {
  const [settings, setSettings] = useState<SettingsOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [twogisKey, setTwogisKey] = useState("");
  const [llmProvider, setLlmProvider] = useState("openai_compat");
  const [llmBaseUrl, setLlmBaseUrl] = useState("");
  const [llmApiKey, setLlmApiKey] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [llmModels, setLlmModels] = useState<string[]>([]);
  const [userOffer, setUserOffer] = useState("");
  const [extraInstructions, setExtraInstructions] = useState("");

  const [sourceCheck, setSourceCheck] = useState<HealthCheck | null>(null);
  const [llmCheck, setLlmCheck] = useState<HealthCheck | null>(null);
  const [checkingSource, setCheckingSource] = useState(false);
  const [checkingLlm, setCheckingLlm] = useState(false);

  const load = () => {
    api
      .get<SettingsOut>("/settings")
      .then((s) => {
        setSettings(s);
        setLlmProvider(s.llm.provider);
        setLlmBaseUrl(s.llm.base_url);
        setLlmModel(s.llm.model);
        setUserOffer(s.outreach.user_offer);
        setExtraInstructions(s.outreach.extra_instructions);
      })
      .catch((e: ApiError) => setError(e.detail ?? ru.errors.network));
  };

  useEffect(load, []);

  const save = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const source: Record<string, unknown> = {};
      if (twogisKey) source.twogis_api_key = twogisKey;

      const llm: Record<string, unknown> = { provider: llmProvider, base_url: llmBaseUrl, model: llmModel };
      if (llmApiKey) llm.api_key = llmApiKey;

      await api.put("/settings", {
        source,
        llm,
        outreach: { user_offer: userOffer, extra_instructions: extraInstructions },
      });
      setTwogisKey("");
      setLlmApiKey("");
      setSaved(true);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : ru.errors.generic);
    } finally {
      setSaving(false);
    }
  };

  const testSource = async () => {
    setCheckingSource(true);
    setSourceCheck(null);
    try {
      setSourceCheck(await api.post<HealthCheck>("/settings/test/source"));
    } catch (err) {
      setSourceCheck({ ok: false, detail: err instanceof ApiError ? err.detail : ru.errors.generic });
    } finally {
      setCheckingSource(false);
    }
  };

  const testLlm = async () => {
    setCheckingLlm(true);
    setLlmCheck(null);
    try {
      setLlmCheck(await api.post<HealthCheck>("/settings/test/llm"));
    } catch (err) {
      setLlmCheck({ ok: false, detail: err instanceof ApiError ? err.detail : ru.errors.generic });
    } finally {
      setCheckingLlm(false);
    }
  };

  const loadModels = async () => {
    try {
      setLlmModels(await api.get<string[]>("/llm/models"));
    } catch {
      setLlmModels([]);
    }
  };

  if (!settings && !error) return <p className="p-6 text-sm text-gray-500">{ru.app.loading}</p>;

  return (
    <div className="max-w-2xl p-6">
      <h1 className="text-xl font-semibold">{ru.nav.settings}</h1>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {saved && <p className="mt-2 text-sm text-green-700">Сохранено.</p>}

      {settings && (
        <div className="mt-6 flex flex-col gap-8">
          <section>
            <h2 className="font-medium">Источник данных</h2>
            <div className="mt-2 grid gap-2">
              <label className="text-sm text-gray-600">
                2GIS API ключ {settings.source.twogis_api_key_is_set && "(задан)"}
              </label>
              <input
                className="rounded border px-2 py-1 text-sm"
                type="password"
                placeholder={settings.source.twogis_api_key_is_set ? "••••••••" : "sk-..."}
                value={twogisKey}
                onChange={(e) => setTwogisKey(e.target.value)}
              />
              <button
                className="w-fit rounded border px-3 py-1 text-sm disabled:opacity-50"
                onClick={testSource}
                disabled={checkingSource}
                type="button"
              >
                Проверить подключение
              </button>
              {sourceCheck && (
                <p className={`text-sm ${sourceCheck.ok ? "text-green-700" : "text-red-600"}`}>
                  {sourceCheck.detail}
                </p>
              )}
            </div>
          </section>

          <section>
            <h2 className="font-medium">LLM провайдер</h2>
            <div className="mt-2 flex flex-wrap gap-2">
              {LLM_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className="rounded border px-2 py-1 text-xs hover:bg-gray-50"
                  onClick={() => {
                    setLlmProvider(preset.provider);
                    setLlmBaseUrl(preset.base_url);
                  }}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <div className="mt-3 grid gap-2">
              <label className="text-sm text-gray-600">Провайдер</label>
              <select
                className="rounded border px-2 py-1 text-sm"
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value)}
              >
                <option value="openai_compat">OpenAI-совместимый (Ollama, OpenAI, OpenRouter…)</option>
                <option value="anthropic">Anthropic</option>
              </select>

              {llmProvider === "openai_compat" && (
                <>
                  <label className="text-sm text-gray-600">Base URL</label>
                  <input
                    className="rounded border px-2 py-1 text-sm"
                    value={llmBaseUrl}
                    onChange={(e) => setLlmBaseUrl(e.target.value)}
                  />
                </>
              )}

              <label className="text-sm text-gray-600">
                API ключ {settings.llm.api_key_is_set && "(задан)"}
              </label>
              <input
                className="rounded border px-2 py-1 text-sm"
                type="password"
                placeholder={settings.llm.api_key_is_set ? "••••••••" : "пусто — для Ollama не нужен"}
                value={llmApiKey}
                onChange={(e) => setLlmApiKey(e.target.value)}
              />

              <label className="text-sm text-gray-600">Модель</label>
              <div className="flex gap-2">
                <input
                  className="flex-1 rounded border px-2 py-1 text-sm"
                  list="llm-models"
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                />
                <button
                  type="button"
                  className="rounded border px-2 py-1 text-xs"
                  onClick={loadModels}
                >
                  Список моделей
                </button>
              </div>
              <datalist id="llm-models">
                {llmModels.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>

              <button
                className="w-fit rounded border px-3 py-1 text-sm disabled:opacity-50"
                onClick={testLlm}
                disabled={checkingLlm}
                type="button"
              >
                Проверить подключение
              </button>
              {llmCheck && (
                <p className={`text-sm ${llmCheck.ok ? "text-green-700" : "text-red-600"}`}>
                  {llmCheck.detail}
                </p>
              )}
            </div>
          </section>

          <section>
            <h2 className="font-medium">Текст сообщений</h2>
            <div className="mt-2 grid gap-2">
              <label className="text-sm text-gray-600">Наша услуга</label>
              <input
                className="rounded border px-2 py-1 text-sm"
                placeholder="Делаем сайты для локального бизнеса от 90 000 ₸ за 7 дней"
                value={userOffer}
                onChange={(e) => setUserOffer(e.target.value)}
              />
              <label className="text-sm text-gray-600">Дополнительные инструкции</label>
              <textarea
                className="rounded border px-2 py-1 text-sm"
                rows={2}
                value={extraInstructions}
                onChange={(e) => setExtraInstructions(e.target.value)}
              />
            </div>
          </section>

          <button
            className="w-fit rounded bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50"
            onClick={save}
            disabled={saving}
            type="button"
          >
            {ru.common.save}
          </button>
        </div>
      )}
    </div>
  );
}
