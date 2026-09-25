---
description: "What a container really is, why it changed how software ships, and how Docker is put together."
icon: box
---

# 1. Containers and Docker fundamentals

{% hint style="info" %}
**Level:** Beginner · **Part:** Docker essentials
{% endhint %}

## Simple explanation

Every developer has heard “it works on my machine”. The app needs a specific Python version, some system libraries, environment variables and config files, and one of them is always different on the server. A **container** packages the app together with everything it needs, so it runs the same way on your laptop, in CI and in production.

A container is *not* a small virtual machine. It's an ordinary Linux process that the kernel isolates: **namespaces** control what it can see (its own filesystem, process list, network and hostname), and **cgroups** control how much it can use (CPU, memory). Because there's no second operating system to boot, a container starts in milliseconds and weighs megabytes, not gigabytes.

**Docker** is the toolset that made containers easy: it builds **images** (read-only templates), runs **containers** (live instances of an image), and moves images through **registries** (image stores such as Docker Hub or Amazon ECR). Kubernetes, which you'll learn in Part 2, runs exactly these images across many machines.

{% hint style="info" %}
**Analogy**

An image is like a class and a container is like an object created from it. You can start ten containers from one image, and each gets its own writable scratch space while sharing the same read-only files underneath.
{% endhint %}

## Key concepts

| Concept | What it means |
| --- | --- |
| Image | A read-only, layered package of your app, its runtime and libraries. Identified by `name:tag` or an immutable `@sha256:` digest. |
| Container | A running (or stopped) instance of an image, with its own writable layer on top. |
| Dockerfile | A text recipe that tells Docker how to build an image, step by step. |
| Registry | A server that stores images: Docker Hub, Amazon ECR, GitHub Container Registry (GHCR). |
| Repository and tag | `nginx` is a repository; `nginx:1.27` is one tagged version inside it. |
| Layer | Each build step produces a cached layer. Images share common layers on disk and over the network. |
| Namespaces | Kernel feature giving a process its own view of PIDs, network, mounts, users and hostname. |
| cgroups | Kernel feature limiting and measuring CPU, memory and I/O for a group of processes. |
| OCI | The Open Container Initiative standards. Any OCI image runs on Docker, containerd, Podman and Kubernetes. |

## Architecture: VMs versus containers

<figure><img src="../.gitbook/assets/vm-vs-containers.svg" alt="Containers and Docker fundamentals: Architecture: VMs versus containers"><figcaption><p>A VM virtualizes hardware and runs a whole operating system. A container is just an isolated process on the host's kernel, so it starts instantly and uses far less memory.</p></figcaption></figure>

|  | Virtual machine | Container |
| --- | --- | --- |
| Isolates | Hardware (full guest OS) | A process (shared host kernel) |
| Startup | Tens of seconds to minutes | Milliseconds to a few seconds |
| Size | Gigabytes | Megabytes |
| Density | A handful per host | Dozens to hundreds per host |
| Isolation strength | Very strong | Strong, but the kernel is shared |
| Typical use | Different OS kernels, strong multi-tenancy | Packaging and running applications |

## Architecture: how Docker is built

<figure><img src="../.gitbook/assets/docker-architecture.svg" alt="Containers and Docker fundamentals: Architecture: how Docker is built"><figcaption><p>The CLI only sends requests. dockerd builds and manages images, containerd supervises containers, and runc creates each isolated process. Kubernetes uses containerd directly, which is why any Docker image runs there.</p></figcaption></figure>

| Component | Job |
| --- | --- |
| docker CLI | The command you type. It only sends requests to the daemon's REST API. |
| dockerd | The Docker Engine daemon. Builds images (with BuildKit), manages networks, volumes and images. |
| containerd | Supervises containers: pulls images, sets up filesystems, starts and stops. Kubernetes talks to containerd directly. |
| runc | A tiny tool that asks the kernel to create the namespaces and cgroups, then starts your process. |
| Registry | Remote image storage. `docker pull` downloads layers; `docker push` uploads them. |

On macOS and Windows, Docker Desktop runs these Linux components inside a small hidden VM, because containers need a Linux kernel.

## The Docker workflow

<figure><img src="../.gitbook/assets/docker-workflow.svg" alt="Containers and Docker fundamentals: The Docker workflow"><figcaption><p>Build once, run the same image everywhere: your laptop, CI, a server, or a Kubernetes cluster.</p></figcaption></figure>

## Important commands

```bash
docker version            # client and server (daemon) versions
docker info               # storage driver, cgroups, number of containers/images
docker run hello-world    # pull an image and run your first container
docker system df          # disk used by images, containers, volumes, build cache
```

## Hands-on exercises

{% stepper %}
{% step %}
Run `docker run hello-world` and read its output. It lists the four steps Docker took; match each step to a box in the architecture diagram.
{% endstep %}
{% step %}
Prove containers share the kernel: run `uname -r` on your machine (or inside Docker Desktop's VM via `docker run --rm alpine uname -r`), then `docker run --rm ubuntu uname -r`. Same kernel, different distributions.
{% endstep %}
{% step %}
See process isolation: `docker run --rm alpine ps aux`. The container sees only itself, running as PID 1.
{% endstep %}
{% step %}
Run `docker run --rm alpine cat /etc/os-release` and `docker run --rm debian cat /etc/os-release`. Each image brings its own userland files.
{% endstep %}
{% endstepper %}

## Common mistakes and tips

- **Treating a container like a VM.** Don't SSH into containers or run many services in one. One main process per container; rebuild instead of patching by hand.
- **Keeping important data inside the container.** Its writable layer is deleted with it. Use volumes (Module 5).
- **Confusing images and containers.** `docker images` lists templates; `docker ps -a` lists instances.
- **Assuming containers are a security boundary like VMs.** They share the kernel. Run as non-root and keep images minimal (Module 7).
