---
description: "Keeping data safe when containers are replaced."
icon: database
---

# 5. Volumes and persistent data

{% hint style="info" %}
**Level:** Intermediate · **Part:** Docker essentials
{% endhint %}

## Simple explanation

Containers are disposable: remove one and its writable layer, with every file it wrote, is gone. To keep data, you mount storage from *outside* the container into a path inside it. Docker offers three kinds: **named volumes** managed by Docker, **bind mounts** that map a folder from your machine, and **tmpfs** mounts that live in memory.

Kubernetes has the same idea with PersistentVolumeClaims (Module 14).

## Architecture

<figure><img src="../.gitbook/assets/docker-volumes.svg" alt="Volumes and persistent data: Architecture"><figcaption><p>Anything written outside these mounts lands in the container's writable layer and is lost when the container is removed.</p></figcaption></figure>

## Key concepts

| Type | Managed by | Survives container removal? | Best for |
| --- | --- | --- | --- |
| Named volume | Docker (`/var/lib/docker/volumes`) | Yes | Databases, anything the app owns |
| Bind mount | You (any host path) | Yes (it's your folder) | Source code with live reload, config files in dev |
| tmpfs | Memory | No | Scratch space, sensitive temporary files |
| Anonymous volume | Docker, random name | Yes, but hard to find | Avoid; name your volumes |

| Concept | What it means |
| --- | --- |
| `-v` vs `--mount` | Same result. `--mount type=volume,src=pgdata,dst=/data` is more explicit and fails loudly on typos. |
| Read-only | Append `:ro` (`-v ./config:/etc/app:ro`) so the container can't change it. |
| Permissions | Files are owned by numeric UIDs. A container running as UID 10001 needs write access to its mount. |
| Mounting over a path | A mount hides whatever the image had at that path. |

## Important commands

```bash
docker volume create pgdata
docker volume ls
docker volume inspect pgdata
docker run -d --name pg -e POSTGRES_PASSWORD=devpass \
  -v pgdata:/var/lib/postgresql/data postgres:16-alpine

# bind mount the current folder for live development
docker run --rm -p 8080:80 -v "$(pwd)/site:/usr/share/nginx/html:ro" nginx:1.27

# in-memory scratch space
docker run --rm --tmpfs /tmp:size=64m alpine df -h /tmp

docker volume rm pgdata          # deletes the data
docker volume prune              # deletes ALL unused volumes: careful
```

## Example: back up and restore a volume

```bash
# backup pgdata into ./pgdata.tar.gz
docker run --rm -v pgdata:/data:ro -v "$(pwd)":/backup alpine \
  tar czf /backup/pgdata.tar.gz -C /data .

# restore into a new volume
docker volume create pgdata-restored
docker run --rm -v pgdata-restored:/data -v "$(pwd)":/backup alpine \
  tar xzf /backup/pgdata.tar.gz -C /data
```

## Hands-on exercises

{% stepper %}
{% step %}
Run Postgres with the `pgdata` volume, create a table, then `docker rm -f pg`. Start a new container with the same volume: the table is still there.
{% endstep %}
{% step %}
Run Postgres again *without* a volume, create a table, remove the container. The data is gone for good.
{% endstep %}
{% step %}
Serve a local `site/` folder with nginx via a bind mount. Edit `index.html` and refresh: the change is instant, no rebuild.
{% endstep %}
{% step %}
Back up `pgdata`, delete it, restore it into a new volume, and verify the table.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **`docker volume prune` or `docker compose down -v` by habit** — both delete data permanently.
- **`Permission denied` writing to a bind mount** — the container user's UID doesn't own the host folder. Match UIDs or `chown` the folder.
- **Empty folder where the app expected files** — you mounted over a path that had content in the image.
- **Slow bind mounts on macOS** — file sharing crosses the VM boundary. Use named volumes for dependencies like `node_modules`.
- **Databases on bind mounts in production** — possible, but managed databases (RDS/Aurora) remove the backup and failover work entirely.
