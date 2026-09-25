---
description: "Learn containers and Kubernetes from zero, one hands-on module at a time."
icon: house
cover: .gitbook/assets/cover.png
coverY: 0
layout:
  width: default
  cover:
    visible: true
    size: hero
  title:
    visible: true
  description:
    visible: true
  tableOfContents:
    visible: true
  outline:
    visible: true
  pagination:
    visible: true
---

# Docker & Kubernetes from Scratch

Twenty-four modules and a capstone, in order. You start by brushing up on Docker: what a container is, how images are built, how containers talk and keep data, and how Compose runs a whole stack. Then you take those same images to Kubernetes, all the way to autoscaling, monitoring, CI/CD and production practice on AWS.

Every module explains one idea in plain language, shows the commands and YAML, and hands you a lab to run on your own laptop.

<table data-view="cards"><thead><tr><th></th><th></th></tr></thead><tbody>
<tr><td><strong>What you need</strong></td><td>A laptop with 8 GB+ RAM, a terminal and a code editor. You'll install Docker in Module 2. Nothing costs money until Module 23.</td></tr>
<tr><td><strong>How long it takes</strong></td><td>About 35–45 hours: a weekend for Docker, two weekends for Kubernetes basics and workloads, and a week of evenings for production topics and the capstone.</td></tr>
<tr><td><strong>How to study</strong></td><td>Type every command yourself instead of pasting. Break each lab on purpose, then fix it with the troubleshooting tips.</td></tr>
</tbody></table>

## The learning path

Each part builds on the one before it.

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody>
<tr><td><strong>Part 1 · Docker essentials</strong></td><td>Modules 1–7. Containers, images and Dockerfiles, networking, volumes, Compose, registries and security.</td><td><a href=".gitbook/assets/part-docker.png">part-docker.png</a></td><td><a href="docker/01-containers-and-docker-fundamentals.md">01-containers-and-docker-fundamentals.md</a></td></tr>
<tr><td><strong>Part 2 · Kubernetes foundations</strong></td><td>Modules 8–13. Architecture, a local cluster, kubectl, Deployments, Services, config and secrets.</td><td><a href=".gitbook/assets/part-foundations.png">part-foundations.png</a></td><td><a href="kubernetes-foundations/08-kubernetes-fundamentals-and-architecture.md">08-kubernetes-fundamentals-and-architecture.md</a></td></tr>
<tr><td><strong>Part 3 · Running real workloads</strong></td><td>Modules 14–19. Storage, namespaces and quotas, Ingress, probes, RBAC and Helm.</td><td><a href=".gitbook/assets/part-workloads.png">part-workloads.png</a></td><td><a href="workloads/14-volumes-and-storage.md">14-volumes-and-storage.md</a></td></tr>
<tr><td><strong>Part 4 · Operating in production</strong></td><td>Modules 20–24. Autoscaling, monitoring, CI/CD, production practice on AWS, advanced topics.</td><td><a href=".gitbook/assets/part-production.png">part-production.png</a></td><td><a href="production/20-autoscaling.md">20-autoscaling.md</a></td></tr>
<tr><td><strong>Capstone project</strong></td><td>Containerize a Notes API, run it with Docker Compose, then deploy it to Kubernetes with storage, secrets, Ingress, probes, autoscaling and monitoring.</td><td><a href=".gitbook/assets/part-capstone.png">part-capstone.png</a></td><td><a href="capstone/README.md">README.md</a></td></tr>
</tbody></table>

## Every module has the same shape

1. **Simple explanation** of the idea, in plain language.
2. **Key concepts** as a quick-reference table.
3. **Architecture or flow** diagram where it helps.
4. **Important commands** and **examples** you can copy.
5. **Hands-on exercises** to run on your own laptop.
6. **Common mistakes and troubleshooting** from real incidents.

{% hint style="info" %}
**Already comfortable with Docker?** Skim Module 3 (Dockerfiles) and Module 7 (the Docker-to-Kubernetes map), then jump to [Part 2](kubernetes-foundations/08-kubernetes-fundamentals-and-architecture.md).
{% endhint %}

## All modules

### Docker essentials

1. [Containers and Docker fundamentals](docker/01-containers-and-docker-fundamentals.md): What a container really is, why it changed how software ships, and how Docker is put together.
2. [Installing Docker and running containers](docker/02-installing-docker-and-running-containers.md): Install Docker, then learn the container lifecycle with the commands you'll use every day.
3. [Images and Dockerfiles](docker/03-images-and-dockerfiles.md): Package your own application as an image that is small, fast to build and safe to run.
4. [Docker networking](docker/04-docker-networking.md): How containers talk to each other and to the outside world.
5. [Volumes and persistent data](docker/05-volumes-and-persistent-data.md): Keeping data safe when containers are replaced.
6. [Docker Compose](docker/06-docker-compose.md): Define and run a whole multi-container application with one file.
7. [Registries, image security, and the bridge to Kubernetes](docker/07-registries-security-and-the-bridge-to-kubernetes.md): Ship images safely, then see exactly what Kubernetes adds on top of Docker.

### Kubernetes foundations

8. [Kubernetes fundamentals and architecture](kubernetes-foundations/08-kubernetes-fundamentals-and-architecture.md): What Kubernetes is, the problem it solves, and the parts inside a cluster.
9. [Setting up a local Kubernetes cluster](kubernetes-foundations/09-local-cluster-setup.md): A real cluster on your laptop in five minutes, for free.
10. [kubectl basics](kubernetes-foundations/10-kubectl-basics.md): The one command you'll type thousands of times, and how to read what it tells you.
11. [Pods, ReplicaSets, and Deployments](kubernetes-foundations/11-pods-replicasets-deployments.md): How Kubernetes runs your containers and keeps the right number alive.
12. [Services and networking](kubernetes-foundations/12-services-and-networking.md): Giving a changing group of Pods one stable address.
13. [ConfigMaps and Secrets](kubernetes-foundations/13-configmaps-and-secrets.md): Keeping configuration out of your images.

### Running real workloads

14. [Volumes and persistent storage](workloads/14-volumes-and-storage.md): Data that survives Pod restarts, and when it shouldn't live in the cluster at all.
15. [Namespaces and resource management](workloads/15-namespaces-and-resources.md): Dividing a cluster between teams and environments, and stopping one app from starving the rest.
16. [Ingress](workloads/16-ingress.md): One entry point that routes HTTP traffic by hostname and path.
17. [Health checks and probes](workloads/17-health-checks-and-probes.md): Teaching Kubernetes the difference between "running" and "working".
18. [Security and RBAC](workloads/18-security-and-rbac.md): Who can do what in the cluster, and what your containers are allowed to do.
19. [Helm](workloads/19-helm.md): Packaging, templating, and versioning your Kubernetes YAML.

### Operating in production

20. [Autoscaling](production/20-autoscaling.md): More Pods when busy, more nodes when Pods don't fit, fewer of both when quiet.
21. [Monitoring and troubleshooting](production/21-monitoring-and-troubleshooting.md): Seeing inside the cluster, and a repeatable method for fixing what's broken.
22. [Kubernetes in CI/CD](production/22-kubernetes-in-ci-cd.md): From git push to a verified rollout, with push and GitOps pipelines.
23. [Production best practices](production/23-production-best-practices.md): A checklist distilled from outages, and what a real cluster on AWS looks like.
24. [Advanced Kubernetes concepts](production/24-advanced-concepts.md): The tools you'll meet once the basics are second nature.

### Capstone

25. [Capstone project](capstone/README.md): every module combined into one working system.
