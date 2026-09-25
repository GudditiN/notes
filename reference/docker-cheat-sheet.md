---
description: "Every Docker and Compose command from Part 1, in one place."
icon: box
---

# Docker cheat sheet

| Task | Command |
| --- | --- |
| Run a container in the background | `docker run -d --name web -p 8080:80 nginx:1.27` |
| Throwaway interactive shell | `docker run --rm -it ubuntu:24.04 bash` |
| List running / all containers | `docker ps / docker ps -a` |
| Logs (follow) | `docker logs -f NAME` |
| Shell into a running container | `docker exec -it NAME sh` |
| Stop, start, remove | `docker stop NAME, docker start NAME, docker rm -f NAME` |
| Inspect one field | `docker inspect -f '{{.State.Status}}' NAME` |
| Live CPU and memory | `docker stats` |
| Build and tag an image | `docker build -t app:1.0.0 .` |
| See image layers | `docker history app:1.0.0` |
| Multi-arch build and push | `docker buildx build --platform linux/amd64,linux/arm64 -t REG/app:1.0.0 --push .` |
| Tag and push | `docker tag app:1.0.0 REG/app:1.0.0 && docker push REG/app:1.0.0` |
| Log in to ECR | `aws ecr get-login-password \| docker login --username AWS --password-stdin REG` |
| Create a network | `docker network create app-net` |
| Run on a network | `docker run -d --network app-net --name db postgres:16-alpine` |
| Named volume | `docker run -v pgdata:/var/lib/postgresql/data ...` |
| Bind mount (read-only) | `docker run -v "$(pwd)/site:/usr/share/nginx/html:ro" ...` |
| Compose up with build | `docker compose up -d --build` |
| Compose logs / exec | `docker compose logs -f api / docker compose exec db sh` |
| Compose down (keep / delete data) | `docker compose down / docker compose down -v` |
| Scan an image | `trivy image --severity HIGH,CRITICAL app:1.0.0` |
| Disk usage and cleanup | `docker system df, docker system prune` |

{% hint style="warning" %}
**Destructive commands:** `docker system prune -a`, `docker volume prune` and `docker compose down -v` delete images or data permanently. Read the prompt before typing `y`.
{% endhint %}
