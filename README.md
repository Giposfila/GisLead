# LeadGis

Полностью локальный, open-source инструмент для лидогенерации: собирает
организации из 2GIS по нише и городу, проверяет наличие сайта и мессенджеров,
генерирует персонализированные сообщения через LLM и показывает всё в
мини-CRM в браузере — без облачного сервера и без телеметрии.

*A fully local, open-source lead-generation tool: collects businesses from
2GIS by niche and city, checks for a website/messengers, drafts a
personalized outreach message via an LLM, and shows everything in a
browser-based mini-CRM — no vendor server, no telemetry.*

## Быстрый старт / Quickstart

### Из исходников (для разработки) / From source (development)

```bash
pip install -e ".[dev]"
cd frontend && npm install && npm run build && cd ..
leadgis start
```

### pipx (для обычной установки) / pipx (regular install)

Соберите фронтенд *до* установки пакета — он собирается в `leadgis/webui/`
и попадает внутрь wheel:

*Build the frontend **before** installing the package — it builds into
`leadgis/webui/` and ships inside the wheel:*

```bash
cd frontend && npm install && npm run build && cd ..
pipx install .
leadgis start
```

В любом случае откроется `http://127.0.0.1:8000`. Конфигурация —
`~/.leadgis/config.toml`, база данных — `~/.leadgis/leadgis.db` (создаются
автоматически при первом запуске). Дальше: Settings → выберите LLM (Ollama
локально не требует ключа) → создайте кампанию → «Собрать лиды» → «Сгенерировать».

*Either way this opens `http://127.0.0.1:8000`. Config and DB are created
automatically on first run. Next: Settings → pick an LLM (Ollama needs no
key) → create a campaign → collect leads → generate messages.*

## Разработка / Development

```bash
# backend
ruff check . && ruff format --check . && mypy leadgis && pytest

# frontend dev server (proxies /api to :8000)
cd frontend && npm run dev
```

## Источники данных / Data sources

Источник выбирается отдельно для каждой кампании (при создании), ключи — в
Settings:

- [2GIS Catalog API](https://dev.2gis.com/) — рейтинг и отзывы есть всегда;
  телефон/сайт/соцсети зависят от тарифа ключа (демо-ключи их не отдают).
- [Yandex Maps Places API](https://developer.tech.yandex.com/) — телефон и
  сайт есть; рейтинга, отзывов, Instagram и Telegram у сервиса нет вообще
  (не тариф, а факт API).

Опциональный Playwright-скрапер (`pip install leadgis[scraper]`) —
использовать с осторожностью, см. раздел "Legal/compliance" ниже.

## Отправка сообщений / Sending

Отправка **полуавтоматическая**: приложение открывает предзаполненную
ссылку `wa.me`/`t.me`, отправляет человек. Массовой автоматической рассылки
в ядре нет и не будет — это осознанное решение (риск блокировки аккаунта +
требования законодательства о рекламе), а не техническое ограничение.

## Legal / compliance

Вы несёте ответственность за соблюдение законодательства о рекламе и
персональных данных в вашей юрисдикции (например, ст. 18 ФЗ "О рекламе" в
РФ — требования о согласии на рекламные рассылки; аналогичные нормы в
РК/РБ), а также условий использования 2GIS API. Скрапер-адаптер (опция)
может нарушать ToS 2GIS — используйте официальный API, когда это возможно.

## License

MIT
