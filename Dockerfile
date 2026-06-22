FROM node:22-alpine AS handoff-ui

WORKDIR /ui

COPY handoff-ui/package.json handoff-ui/package-lock.json ./
RUN npm ci

COPY handoff-ui/ ./
RUN npm run build


FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-kor \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY --from=handoff-ui /ui/dist ./handoff-ui/dist

RUN pip install --no-cache-dir .

ENV HANDOFF_UI_DIST=/app/handoff-ui/dist \
    PORT=8080

EXPOSE 8080

CMD ["talkcheck"]
