---
description: "Giving a changing group of Pods one stable address."
icon: network-wired
---

# 12. Services and networking

{% hint style="info" %}
**Level:** Beginner → Intermediate · **Part:** Kubernetes foundations
{% endhint %}

## Simple explanation

Pods come and go, and each new one gets a new IP. A **Service** gives a group of Pods (selected by label) a single stable IP and DNS name, and load-balances traffic across whichever of those Pods are currently Ready.

Kubernetes networking follows three rules: every Pod gets its own IP; every Pod can reach every other Pod without NAT; and agents on a node can reach all Pods on it. A **CNI plugin** (Calico, Cilium, AWS VPC CNI, kind's kindnet) implements those rules.

## Key concepts: Service types

| Type | Reachable from | Use it for |
| --- | --- | --- |
| **ClusterIP** (default) | Inside the cluster only | Service-to-service calls (API → DB, frontend → API) |
| **NodePort** | Every node's IP on a port 30000–32767 | Quick testing, bare-metal setups |
| **LoadBalancer** | A cloud load balancer's public/private IP | Exposing one service directly on cloud (NLB on AWS) |
| **ExternalName** | DNS CNAME to something outside | Pointing `db` at an RDS hostname |
| **Headless** (`clusterIP: None`) | DNS returns Pod IPs directly | StatefulSets, databases, client-side load balancing |

| Concept | What it means |
| --- | --- |
| Endpoints / EndpointSlices | The live list of Pod IPs behind a Service. Empty list = your selector matches nothing Ready. |
| port / targetPort | `port` is what clients call on the Service; `targetPort` is the container's port. |
| CoreDNS | Cluster DNS. `web` resolves inside the same namespace; `web.shop` or `web.shop.svc.cluster.local` from anywhere. |
| NetworkPolicy | Firewall rules between Pods (covered in Module 18). |

## Architecture / flow

<figure><img src="../.gitbook/assets/service-networking.svg" alt="How a Service routes traffic to Pods"><figcaption><p>① The client looks up the Service name in CoreDNS. ② It connects to the stable ClusterIP. ③ kube-proxy rules on the node forward the connection to one Ready Pod listed in the EndpointSlice.</p></figcaption></figure>

<table data-view="cards"><thead><tr><th></th><th></th></tr></thead><tbody><tr><td><strong>Stable name</strong></td><td>The Service's DNS name and ClusterIP never change, however many times Pods are replaced.</td></tr><tr><td><strong>Live membership</strong></td><td>The EndpointSlice lists only Pods that match the selector <em>and</em> are Ready. It updates within seconds.</td></tr><tr><td><strong>Node-local routing</strong></td><td>No proxy Pod sits in the middle. kube-proxy on every node rewrites the destination to a Pod IP.</td></tr></tbody></table>

## YAML examples

{% code title="service-clusterip.yaml" %}
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  type: ClusterIP
  selector:
    app: web                 # sends traffic to Pods with this label
  ports:
    - name: http
      port: 80               # Service port
      targetPort: 80         # container port (can also be a named port)
```
{% endcode %}

{% code title="service-nodeport.yaml" %}
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-nodeport
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080        # optional; auto-assigned if omitted
```
{% endcode %}

{% code title="service-lb-aws.yaml" %}
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-public
  annotations:                                   # AWS Load Balancer Controller
    service.beta.kubernetes.io/aws-load-balancer-type: external
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
spec:
  type: LoadBalancer
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
```
{% endcode %}

{% code title="externalname.yaml" %}
```yaml
apiVersion: v1
kind: Service
metadata:
  name: db
spec:
  type: ExternalName
  externalName: mydb.cluster-abc123.ap-south-1.rds.amazonaws.com
```
{% endcode %}

## Important commands

```bash
kubectl expose deploy web --port=80 --target-port=80          # quick ClusterIP
kubectl get svc,endpointslices -l app=web
kubectl describe svc web                                       # check "Endpoints:" line
kubectl port-forward svc/web 8080:80                           # reach it from laptop
kubectl run curl --image=curlimages/curl:8.10.1 --rm -it --restart=Never -- curl -s http://web
kubectl run dns --image=busybox:1.36 --rm -it --restart=Never -- nslookup web.default.svc.cluster.local
```

## Hands-on exercises

{% stepper %}
{% step %}
With the `web` Deployment running, apply the ClusterIP Service and curl it from a throwaway Pod.
{% endstep %}
{% step %}
Make each nginx Pod return its hostname: `kubectl exec POD -- sh -c 'echo $HOSTNAME > /usr/share/nginx/html/index.html'` for each Pod. Curl the Service 10 times and watch load balancing.
{% endstep %}
{% step %}
Scale to 0 and check `kubectl get endpointslices`. Curl fails. Scale back up.
{% endstep %}
{% step %}
Change the Service selector to `app: wrong` and diagnose it using only `describe`.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **Service has no endpoints** — selector doesn't match Pod labels, or Pods aren't Ready (failing readiness probe). Compare `kubectl get pods --show-labels` with the selector.
- **Connection refused** — `targetPort` doesn't match the port the app actually listens on. Also check the app binds to `0.0.0.0`, not `127.0.0.1`.
- **DNS fails across namespaces** — use `service.namespace`, not just `service`.
- **One LoadBalancer per service** gets expensive fast on cloud. Use one Ingress (Module 16) for all HTTP services.
- You can't `ping` a ClusterIP — it's a virtual IP that only handles the declared TCP/UDP ports. Test with curl.
