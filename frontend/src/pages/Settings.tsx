import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { ru } from "../i18n/ru";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import Icon from "../components/Icon";

interface SettingsOut {
  app: {
    host: string;
    port: number;
    open_browser: boolean;
    auth_token_is_set: boolean;
  };
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
  outreach: {
    user_offer: string;
    extra_instructions: string;
    template: string;
  };
}

interface HealthCheck {
  ok: boolean;
  detail: string;
}

const LLM_PRESETS: { label: string; provider: string; base_url: string }[] = [
  {
    label: "Ollama (локально)",
    provider: "openai_compat",
    base_url: "http://localhost:11434/v1",
  },
  {
    label: "OpenAI",
    provider: "openai_compat",
    base_url: "https://api.openai.com/v1",
  },
  {
    label: "OpenRouter",
    provider: "openai_compat",
    base_url: "https://openrouter.ai/api/v1",
  },
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

      const llm: Record<string, unknown> = {
        provider: llmProvider,
        base_url: llmBaseUrl,
        model: llmModel,
      };
      if (llmApiKey) llm.api_key = llmApiKey;

      await api.put("/settings", {
        source,
        llm,
        outreach: {
          user_offer: userOffer,
          extra_instructions: extraInstructions,
        },
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
      const body: Record<string, unknown> = {};
      if (twogisKey) body.twogis_api_key = twogisKey;
      setSourceCheck(
        await api.post<HealthCheck>("/settings/test/source", body),
      );
    } catch (err) {
      setSourceCheck({
        ok: false,
        detail: err instanceof ApiError ? err.detail : ru.errors.generic,
      });
    } finally {
      setCheckingSource(false);
    }
  };

  const llmOverride = (): Record<string, unknown> => {
    const body: Record<string, unknown> = {
      provider: llmProvider,
      base_url: llmBaseUrl,
      model: llmModel,
    };
    if (llmApiKey) body.api_key = llmApiKey;
    return body;
  };

  const testLlm = async () => {
    setCheckingLlm(true);
    setLlmCheck(null);
    try {
      setLlmCheck(
        await api.post<HealthCheck>("/settings/test/llm", llmOverride()),
      );
    } catch (err) {
      setLlmCheck({
        ok: false,
        detail: err instanceof ApiError ? err.detail : ru.errors.generic,
      });
    } finally {
      setCheckingLlm(false);
    }
  };

  const loadModels = async () => {
    setError(null);
    try {
      setLlmModels(await api.post<string[]>("/llm/models", llmOverride()));
    } catch {
      setLlmModels([]);
      setError(ru.settings.modelError);
    }
  };

  const t = ru.settings;
  return (
    <div className="page settings-page">
      <PageHeader title={ru.nav.settings} description={t.description} />
      <Link to="/guide" className="settings-help">
        <Icon name="book" size={19} />
        <span>{t.help}</span>
        <strong>{t.helpLink}</strong>
        <Icon name="arrow" size={16} />
      </Link>
      {error && (
        <div className="alert alert-error" role="alert">
          {error}
          {!settings && (
            <button className="text-link" onClick={load}>
              {ru.common.retry}
            </button>
          )}
        </div>
      )}
      {saved && (
        <div className="alert alert-success" role="status">
          <Icon name="check" size={17} />
          {t.saved}
        </div>
      )}
      {!settings && !error && (
        <div className="loading-state" role="status">
          <span className="spinner" />
          {ru.app.loading}
        </div>
      )}
      {settings && (
        <form
          className="settings-form"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
          onChange={() => setSaved(false)}
        >
          <section className="settings-section">
            <div className="section-description">
              <h2>{t.source}</h2>
              <p>{t.sourceHelp}</p>
            </div>
            <div className="section-fields">
              <label className="field" htmlFor="twogis-key">
                {t.key}
                {settings.source.twogis_api_key_is_set && (
                  <span className="configured">
                    <Icon name="check" size={13} />
                    {t.configured}
                  </span>
                )}
              </label>
              <input
                id="twogis-key"
                type="password"
                autoComplete="new-password"
                placeholder={
                  settings.source.twogis_api_key_is_set
                    ? "••••••••"
                    : "2GIS API"
                }
                value={twogisKey}
                onChange={(e) => {
                  setTwogisKey(e.target.value);
                  setSourceCheck(null);
                }}
              />
              <p className="field-hint">{t.savedKeyHint}</p>
              <button
                className="button button-secondary"
                type="button"
                onClick={testSource}
                disabled={checkingSource}
              >
                {checkingSource ? t.testing : t.test}
                <Icon name="arrow" size={15} />
              </button>
              {sourceCheck && (
                <p
                  role="status"
                  className={`check-result ${sourceCheck.ok ? "success" : "failure"}`}
                >
                  {sourceCheck.detail}
                </p>
              )}
            </div>
          </section>
          <section className="settings-section">
            <div className="section-description">
              <h2>{t.llm}</h2>
              <p>{t.llmHelp}</p>
            </div>
            <div className="section-fields">
              <div className="provider-presets">
                {LLM_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    aria-pressed={
                      llmProvider === preset.provider &&
                      llmBaseUrl === preset.base_url
                    }
                    className={
                      llmProvider === preset.provider &&
                      llmBaseUrl === preset.base_url
                        ? "selected"
                        : ""
                    }
                    onClick={() => {
                      setLlmProvider(preset.provider);
                      setLlmBaseUrl(preset.base_url);
                      setLlmCheck(null);
                      setSaved(false);
                    }}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              <label className="field" htmlFor="provider">
                {t.provider}
              </label>
              <select
                id="provider"
                value={llmProvider}
                onChange={(e) => {
                  setLlmProvider(e.target.value);
                  setLlmCheck(null);
                }}
              >
                <option value="openai_compat">
                  OpenAI-compatible / Ollama
                </option>
                <option value="anthropic">Anthropic</option>
              </select>
              {llmProvider === "openai_compat" && (
                <>
                  <label className="field" htmlFor="base-url">
                    {t.baseUrl}
                  </label>
                  <input
                    id="base-url"
                    type="url"
                    required
                    value={llmBaseUrl}
                    onChange={(e) => {
                      setLlmBaseUrl(e.target.value);
                      setLlmCheck(null);
                    }}
                  />
                </>
              )}
              <label className="field" htmlFor="llm-key">
                {t.apiKey}
                {settings.llm.api_key_is_set && (
                  <span className="configured">
                    <Icon name="check" size={13} />
                    {t.configured}
                  </span>
                )}
              </label>
              <input
                id="llm-key"
                type="password"
                autoComplete="new-password"
                placeholder={settings.llm.api_key_is_set ? "••••••••" : t.noKey}
                value={llmApiKey}
                onChange={(e) => {
                  setLlmApiKey(e.target.value);
                  setLlmCheck(null);
                }}
              />
              <p className="field-hint">{t.savedKeyHint}</p>
              <label className="field" htmlFor="llm-model">
                {t.model}
              </label>
              <div className="model-field">
                <input
                  id="llm-model"
                  required
                  list="llm-models"
                  value={llmModel}
                  onChange={(e) => {
                    setLlmModel(e.target.value);
                    setLlmCheck(null);
                  }}
                />
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={loadModels}
                >
                  {t.models}
                </button>
              </div>
              <datalist id="llm-models">
                {llmModels.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
              <button
                className="button button-secondary"
                type="button"
                onClick={testLlm}
                disabled={checkingLlm}
              >
                {checkingLlm ? t.testing : t.test}
                <Icon name="arrow" size={15} />
              </button>
              {llmCheck && (
                <p
                  role="status"
                  className={`check-result ${llmCheck.ok ? "success" : "failure"}`}
                >
                  {llmCheck.detail}
                </p>
              )}
            </div>
          </section>
          <section className="settings-section">
            <div className="section-description">
              <h2>{t.outreach}</h2>
              <p>{t.outreachHelp}</p>
            </div>
            <div className="section-fields">
              <label className="field" htmlFor="offer">
                {t.offer}
              </label>
              <textarea
                id="offer"
                rows={3}
                placeholder={t.offerPlaceholder}
                value={userOffer}
                onChange={(e) => setUserOffer(e.target.value)}
              />
              <label className="field" htmlFor="instructions">
                {t.instructions}
              </label>
              <textarea
                id="instructions"
                rows={3}
                placeholder={t.instructionsPlaceholder}
                value={extraInstructions}
                onChange={(e) => setExtraInstructions(e.target.value)}
              />
            </div>
          </section>
          <div className="settings-save">
            <span>
              <Icon name="shield" size={16} />
              {ru.app.local}
            </span>
            <button
              className="button button-primary"
              disabled={saving}
              type="submit"
            >
              <Icon name="check" size={17} />
              {saving ? t.saving : ru.common.save}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
