FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
# vite outputs to ../leadgis/webui (see vite.config.ts) so it lands inside
# the package before `pip install .` builds the wheel below.
RUN npm run build

FROM python:3.12-slim AS backend
WORKDIR /app
COPY pyproject.toml README.md ./
COPY leadgis/ ./leadgis/
COPY --from=frontend /app/leadgis/webui ./leadgis/webui
RUN pip install --no-cache-dir .

ENV LEADGIS_APP__HOST=0.0.0.0
ENV LEADGIS_APP__OPEN_BROWSER=false
EXPOSE 8000
VOLUME ["/root/.leadgis"]

CMD ["leadgis", "start"]
