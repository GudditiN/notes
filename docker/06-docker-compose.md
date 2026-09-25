---
description: "Define and run a whole multi-container application with one file."
icon: boxes-stacked
---

# 6. Docker Compose

{% hint style="info" %}
**Level:** Intermediate · **Part:** Docker essentials
{% endhint %}

## Simple explanation

Typing long `docker run` commands for an API, a database and a cache gets old fast. **Docker Compose** lets you describe all of them in `compose.yaml`: which image or Dockerfile, ports, environment variables, volumes and startup order. Then `docker compose up` creates a private network, starts everything in the right order, and `docker compose down` removes it.

Compose is ideal for local development and CI. It runs on one machine, though. When you need many machines, self-healing and rolling updates, you move to Kubernetes, and a Compose file maps almost one-to-one to Kubernetes objects (Module 7).

## Architecture

<figure><img src="../.gitbook/assets/compose-stack.svg" alt="Docker Compose: Architecture"><figcaption><p>One file declares every service, the network between them and their volumes. docker compose up builds, creates and starts them in dependency order.</p></figcaption></figure>

## Key concepts

| Concept | What it means |
| --- | --- |
| services | Each service becomes one or more containers. Its name is also its DNS name on the project network. |
| image / build | Use an existing image, or build from a folder with a Dockerfile (both: build and tag it). |
| ports | `"8000:8000"` publishes like `-p`. Always quote port mappings in YAML. |
| environment / env_file | Set variables inline or from a file. `${VAR}` is filled from your shell or a `.env` file. |
| volumes | Named volumes declared at the bottom persist between `up` and `down`. |
| healthcheck | A command Compose runs to decide if a service is healthy. |
| depends_on + condition | `condition: service_healthy` waits for the dependency's healthcheck, not just its start. |
| profiles | Optional services started only with `--profile tools`. |
| compose.override.yaml | Automatically merged on top of `compose.yaml`; great for dev-only settings. |

## Example: API + Postgres + Adminer

{% code title="compose.yaml" %}
```yaml
services:
  api:
    build: ./hello-api
    image: hello-api:dev
    ports:
      - "8000:8000"
    environment:
      GREETING: hello from compose
      DB_HOST: db
      DB_PASSWORD: ${DB_PASSWORD:?set DB_PASSWORD in .env}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app"]
      interval: 5s
      timeout: 3s
      retries: 10

  adminer:                      # database UI, only with --profile tools
    image: adminer:4
    ports:
      - "8081:8080"
    profiles: ["tools"]

volumes:
  pgdata:
```
{% endcode %}

{% code title=".env" %}
```text
DB_PASSWORD=change-me
```
{% endcode %}

## Important commands

```bash
docker compose up -d --build          # build images and start in background
docker compose ps                      # status and health
docker compose logs -f api             # follow one service's logs
docker compose exec db psql -U postgres -d app
docker compose --profile tools up -d   # include optional services
docker compose config                  # print the final merged config
docker compose restart api
docker compose down                    # stop and remove containers + network
docker compose down -v                 # ...and delete volumes (data!)
docker compose watch                   # rebuild/sync on file changes (needs a develop: section)
```

## Hands-on exercises

{% stepper %}
{% step %}
Put `hello-api` from Module 3 next to this `compose.yaml`, create `.env`, and run `docker compose up -d --build`. Curl `localhost:8000`.
{% endstep %}
{% step %}
Run `docker compose ps` and watch `db` go from `starting` to `healthy` before `api` starts.
{% endstep %}
{% step %}
Open Adminer with `--profile tools` at `localhost:8081` (server: `db`) and create a table.
{% endstep %}
{% step %}
Run `docker compose down` then `up`: the table survives. Run `down -v` then `up`: it's gone.
{% endstep %}
{% step %}
Remove `DB_PASSWORD` from `.env` and run `up`. Read the clear error from the `:?` syntax.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **`depends_on` without a healthcheck** — the API starts before Postgres accepts connections and crashes. Add a healthcheck and `condition: service_healthy`, and make the app retry anyway.
- **Connecting to `localhost:5432` from the API** — use the service name `db`.
- **Secrets committed in `compose.yaml`** — reference `${VARS}` and keep `.env` out of Git (commit a `.env.example`).
- **The old `version:` key** — it's obsolete; modern Compose ignores it and warns.
- **Changes not picked up** — `up` reuses the existing image. Add `--build` after code changes.
- **Using Compose as a production cluster** — it has no multi-host scheduling or rolling updates. That's what Kubernetes is for.
