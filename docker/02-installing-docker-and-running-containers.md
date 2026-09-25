---
description: "Install Docker, then learn the container lifecycle with the commands you'll use every day."
icon: play
---

# 2. Installing Docker and running containers

{% hint style="info" %}
**Level:** Beginner · **Part:** Docker essentials
{% endhint %}

## Simple explanation

With Docker installed, `docker run` is the command that does most of the work: it pulls the image if needed, creates a container, and starts it. A handful of flags decide how the container behaves: whether it runs in the background, which ports your machine forwards to it, which environment variables it sees, and whether it's deleted when it stops.

## Install Docker

{% tabs %}

{% tab title="macOS" %}

```bash
brew install --cask docker
open -a Docker                      # start Docker Desktop once to finish setup
```

{% endtab %}

{% tab title="Linux" %}

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER       # run docker without sudo
newgrp docker                       # or log out and back in
```

{% endtab %}

{% tab title="Windows" %}

```powershell
winget install -e --id Docker.DockerDesktop
```

{% endtab %}

{% endtabs %}

```bash
docker run hello-world
```

{% hint style="info" %}
**Give Docker enough resources**

In Docker Desktop settings, allocate at least 4 CPUs and 6–8 GB of memory. You'll need it when you run Kubernetes clusters inside Docker in Part 2.
{% endhint %}

## Key concepts

| Concept | What it means |
| --- | --- |
| -d | Detached: run in the background and print the container ID. |
| -it | Interactive terminal: keep STDIN open and attach a TTY, for shells. |
| -p host:container | Publish a port: traffic to `localhost:8080` goes to the container's port 80. |
| -e KEY=value | Set an environment variable. `--env-file .env` loads many. |
| --name | A friendly name instead of a random one like `happy_turing`. |
| --rm | Delete the container automatically when it exits. |
| --restart | Restart policy: `no`, `on-failure`, `unless-stopped`, `always`. |
| Foreground process | A container lives exactly as long as its main process (PID 1). When it exits, the container stops. |

## Flow: the container lifecycle

<figure><img src="../.gitbook/assets/container-lifecycle.svg" alt="Installing Docker and running containers: Flow: the container lifecycle"><figcaption><p>A stopped container still exists with its writable layer until you remove it. docker run is create + start in one step.</p></figcaption></figure>

## Important commands

| Goal | Command |
| --- | --- |
| Run in background | `docker run -d --name web -p 8080:80 nginx:1.27` |
| List running / all | `docker ps` / `docker ps -a` |
| Logs (follow) | `docker logs -f web` |
| Shell inside | `docker exec -it web sh` |
| Run a one-off command | `docker exec web nginx -v` |
| Stop / start / restart | `docker stop web`, `docker start web`, `docker restart web` |
| Remove | `docker rm web` (add `-f` to stop and remove) |
| Details as JSON | `docker inspect web` |
| One field | `docker inspect -f '{{.State.Status}}' web` |
| Live resource use | `docker stats` |
| Copy files | `docker cp web:/etc/nginx/nginx.conf .` |
| Clean up stopped containers | `docker container prune` |

## Examples

```bash
# a web server on http://localhost:8080
docker run -d --name web -p 8080:80 nginx:1.27

# a database with environment variables
docker run -d --name pg -p 5432:5432 \
  -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=app \
  postgres:16-alpine
docker exec -it pg psql -U postgres -d app -c "select version();"

# an interactive, throwaway Ubuntu shell
docker run --rm -it ubuntu:24.04 bash

# limit resources (the same cgroups Kubernetes uses)
docker run -d --name capped --memory 256m --cpus 0.5 nginx:1.27
```

## Hands-on exercises

{% stepper %}
{% step %}
Run nginx on port 8080 and open `http://localhost:8080`. Then run a second nginx on port 8081 from the same image.
{% endstep %}
{% step %}
Change the page: `docker exec web sh -c 'echo hello from docker > /usr/share/nginx/html/index.html'`. Stop and start the container: the change survives. Remove it and run a new one: the change is gone.
{% endstep %}
{% step %}
Start the Postgres container, connect with `psql` through `docker exec`, and create a table.
{% endstep %}
{% step %}
Run `docker run -d --restart unless-stopped --name r nginx:1.27`, kill its main process with `docker exec r nginx -s stop`, and watch Docker restart it with `docker ps`.
{% endstep %}
{% step %}
Use `docker inspect` and `-f` to print the container's IP address and start time.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **`port is already allocated`** — something else uses that host port. Pick another (`-p 8081:80`) or stop the other container.
- **Container exits immediately** — its main process finished. `docker logs NAME` shows why; `docker run ubuntu` exits because `bash` has no terminal without `-it`.
- **`permission denied … docker.sock`** on Linux — your user isn't in the `docker` group yet. Log out and back in after `usermod`.
- **Hundreds of stopped containers** — use `--rm` for one-offs and `docker container prune` regularly.
- **`docker stop` takes 10 seconds** — the app ignores SIGTERM, so Docker waits then kills it. Handle SIGTERM and use the exec form of CMD (Module 3).
