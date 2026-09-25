---
description: "Prove the image and database work together on one machine first."
icon: boxes-stacked
---

# 2. Run it locally with Docker Compose

## Step 3 — Run the stack locally with Docker Compose

Before touching Kubernetes, prove the image and database work together on one machine. This is the same app, the same image and the same environment variables you'll later move into ConfigMaps and Secrets.

{% code title="compose.yaml" %}
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: notes
      POSTGRES_USER: notes
      POSTGRES_PASSWORD: ${DB_PASSWORD:?set DB_PASSWORD in .env}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U notes -d notes"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build: ./app
    image: notes-api:1.0.0
    ports:
      - "8000:8000"
    environment:
      APP_ENV: compose
      LOG_LEVEL: info
      GREETING: hello from docker compose
      DB_HOST: db
      DB_PORT: "5432"
      DB_NAME: notes
      DB_USER: notes
      DB_PASSWORD: ${DB_PASSWORD}
    depends_on:
      db:
        condition: service_healthy
    read_only: true                 # same hardening you'll use in Kubernetes
    tmpfs:
      - /tmp
    user: "10001"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
```
{% endcode %}

{% code title=".env.example" %}
```text
DB_PASSWORD=change-me
```
{% endcode %}

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps                          # wait for both to be healthy
curl -s localhost:8000/ | jq
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"text":"first note, from compose"}' localhost:8000/notes
curl -s localhost:8000/notes | jq
docker compose down                        # data stays in the pgdata volume
docker compose up -d                       # ...and is still there
docker compose down -v                     # clean slate when you're done
```

{% hint style="success" %}
**What maps to what in the next step**

The `db` service becomes a StatefulSet with a PVC, `api` becomes a Deployment behind a Service and Ingress, `environment` splits into a ConfigMap and a Secret, and both healthchecks become readiness and liveness probes.
{% endhint %}
