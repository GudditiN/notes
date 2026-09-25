---
description: "How containers talk to each other and to the outside world."
icon: ethernet
---

# 4. Docker networking

{% hint style="info" %}
**Level:** Intermediate · **Part:** Docker essentials
{% endhint %}

## Simple explanation

Each container gets its own network stack with its own IP address. Containers attached to the same **user-defined network** can reach each other *by name*, because Docker runs a small DNS server for that network. Nothing inside is reachable from your machine unless you **publish** a port with `-p`.

This is the same idea you'll meet in Kubernetes: every Pod gets an IP, and Services give them stable DNS names.

## Architecture

<figure><img src="../.gitbook/assets/docker-networking.svg" alt="Docker networking: Architecture"><figcaption><p>Containers on the same user-defined network reach each other by name through Docker's DNS. Only published ports (-p) are reachable from your machine.</p></figcaption></figure>

## Key concepts: network drivers

| Driver | What it does | Use it for |
| --- | --- | --- |
| `bridge` (default) | Private network on one host, NAT to the outside | Nothing important: no name-based DNS |
| User-defined bridge | Same, plus DNS by container name and better isolation | Almost every multi-container setup |
| `host` | Container shares the host's network directly (Linux) | Maximum network performance, special tools |
| `none` | No networking at all | Batch jobs that must stay offline |
| `overlay` | Spans several hosts (Docker Swarm) | Multi-host setups; Kubernetes replaces this |

| Concept | What it means |
| --- | --- |
| Publishing | `-p 8080:80` maps host port 8080 to container port 80. `-p 127.0.0.1:8080:80` keeps it local to your machine. |
| Embedded DNS | On user-defined networks, `127.0.0.11` answers lookups for container names and `--network-alias` names. |
| Inside vs outside | Inside a container, `localhost` means the container itself, not your laptop or another container. |
| host.docker.internal | Docker Desktop's name for your host machine, handy for reaching a service running outside Docker. |

## Important commands

```bash
docker network ls
docker network create app-net
docker network inspect app-net
docker run -d --name db --network app-net -e POSTGRES_PASSWORD=devpass postgres:16-alpine
docker run -d --name api --network app-net -p 8000:8000 \
  -e DB_HOST=db -e DB_PASSWORD=devpass myapi:1.0.0
docker network connect app-net some-container
docker port api                      # which ports are published
```

## Example: debug networking from inside

```bash
# netshoot contains curl, dig, nc, tcpdump...
docker run --rm -it --network app-net nicolaka/netshoot
dig db                  # resolves to the db container's IP
nc -zv db 5432          # is the port open?
curl -s http://api:8000/healthz
```

## Hands-on exercises

{% stepper %}
{% step %}
Start two alpine containers on the **default** bridge and try `ping` by name. It fails.
{% endstep %}
{% step %}
Create `app-net`, start two containers on it, and ping by name. It works.
{% endstep %}
{% step %}
Run Postgres on `app-net` without `-p`. Connect from a netshoot container on the same network (works) and from your laptop (fails). That's isolation.
{% endstep %}
{% step %}
Publish nginx with `-p 127.0.0.1:8080:80` and confirm it isn't reachable from another device on your Wi-Fi.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **Using `localhost` to reach another container** — use its container or service name on a shared network.
- **App listens on `127.0.0.1` inside the container** — published ports can't reach it. Bind to `0.0.0.0`.
- **Thinking `EXPOSE` opens a port** — it's documentation. Only `-p` publishes.
- **Published ports bypassing the Linux firewall** — Docker writes its own iptables rules, so `ufw deny` doesn't block `-p 5432:5432`. Bind databases to `127.0.0.1` or don't publish them.
- **Host networking on Mac/Windows** behaves differently because containers run inside a VM. Prefer published ports.
