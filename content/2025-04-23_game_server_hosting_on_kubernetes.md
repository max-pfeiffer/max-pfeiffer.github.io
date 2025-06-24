Title: Hosting Game Servers on Bare Metal Kubernetes with kube-vip  
Description: A guide for hosting dedicated game servers on Kubernetes with kube-vip    
Summary: A guide for hosting dedicated game servers on Kubernetes with kube-vip
Date: 2025-04-23 13:00
Author: Max Pfeiffer
Lang: en
Keywords: Game Server, UDP, kupe-vip, Kubernetes
Image: https://max-pfeiffer.github.io/blog/images/2025-04-23_game_server_hosting_on_kubernetes.png

Hosting game servers on Kubernetes is rather straight forward if you use the offerings of the main
cloud providers like [AWS](https://aws.amazon.com/gametech/game-backend-infrastructure/)
or [Google](https://games.withgoogle.com/solutions/create-great-games/host/). If you were using these cloud offerings,
you might know that this can get rather expensive.

So how are you going to do that on bare metal Kubernetes? There are solutions like [Agones](https://github.com/googleforgames/agones)
if you want to become very serious about it and want to run some game server farm. 

But what if you happen to run your own Kubernetes clusters on bare metal and just want to host a couple of game servers
with low effort (like I do)? In this article, I will sketch out the solution I found for my use case.

## UDP protocol
Usually dedicated game servers use UDP protocol for their client communication. Handling the network traffic for UDP
protocol is a bit challenging with Kubernetes: [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
only supports TCP/HTTP protocols. Therefore, leveraging an ingress controller for this task is pointless.

So how can we handle the incoming UDP traffic and forward it to the game server in Kubernetes? The First part of the
solution is a [Service](https://kubernetes.io/docs/concepts/services-networking/service/) of type LoadBalancer. Here
we need to declare all ports the game server uses and connect them via
[EndPoints](https://kubernetes.io/docs/reference/kubernetes-api/service-resources/endpoints-v1/) to the
Deployment/Statefulset which runs the game server. Cloud provider's load balancers then connect to that Service and
configure the `ingress` in the `status.loadbalancer` field of that Service. For instance:
```yaml
apiVersion: v1
kind: Service
status:
  loadBalancer:
    ingress:
    - ip: 111.112.12.34
      ipMode: VIP
      ports:
      - port: 28015
        protocol: UDP
      - port: 28016
        protocol: UDP
      - port: 28016
        protocol: TCP
      - port: 28017
        protocol: UDP
      - port: 28082
        protocol: TCP
```
So an external IP address becomes assigned to that Service. The ingress traffic is routed to that service. And usually
egress traffic is routed through that external IP address as well. 

## kube-vip
How can we achieve this on bare metal Kubernetes? This is where the [kube-vip](https://kube-vip.io/) project kicks in.

![2025-04-23_game_server_hosting_on_kubernetes.png]({static}/images/2025-04-23_game_server_hosting_on_kubernetes.png)

With [kube-vip-cloud-provider](https://github.com/kube-vip/kube-vip-cloud-provider) you can [configure external IP
addresses](https://kube-vip.io/docs/usage/cloud-provider/#the-kube-vip-cloud-provider-configmap) for your Kubernetes
cluster. There are two options:

 * pools of external IP addresses using a ConfigMap (load balanced)
 * single static IP address by annotating a service (not load balanced)

With [kube-vip](https://github.com/kube-vip/kube-vip) you can then connect and configure these external IP addresses to
a Service of type LoadBalancer. This is one of the features of [kube-vip](https://github.com/kube-vip/kube-vip).
Another feature of [kube-vip](https://github.com/kube-vip/kube-vip) is [providing a VIP and doing load balancing for the
Kubernetes control plane](https://kube-vip.io/docs/about/features/). But this is not relevant here and can be
switched off. You can toggle any features [using CLI flags](https://kube-vip.io/docs/installation/flags/).

[kube-vip](https://github.com/kube-vip/kube-vip) can also
[route the egress traffic through the external IP](https://kube-vip.io/docs/usage/egress/) you configured for a service.
This is what we need to use for the Service for our game server. 

## kube-vip installation
I choose to install [kube-vip-cloud-provider](https://github.com/kube-vip/kube-vip-cloud-provider) and
[kube-vip](https://github.com/kube-vip/kube-vip) using [their Helm charts](https://github.com/kube-vip/helm-charts).
This is convenient and works well. For the kube-vip `values.yaml` there are a couple of things to consider: we need to
configure [a special image with iptables to enable the egress-functionality](https://kube-vip.io/docs/usage/egress/#using-kube-vip-egress).
Also, we want to disable the control plane VIP functionality as we only want to use the Service feature. If we want to
[use the egress feature](https://kube-vip.io/docs/usage/kubernetes-services/#external-traffic-policy-kube-vip-v050),
we need to enable the `svc_election` feature. Our `values.yaml` should look like this eventually:
```yaml
image:
  repository: ghcr.io/kube-vip/kube-vip-iptables
  tag: "v0.9.0"

env:
  cp_enable: "false"
  svc_enable: "true"
  svc_election: "true"
```

**Please note:** I discovered [a bug in kube-vip Helm chart](https://github.com/kube-vip/helm-charts/issues/68).
For the ClusterRole, the permission to list pods was missing which was effecting egress config. Until my fix is merged,
you can patch the ClusterRole manually. 

You can install the charts like so:
```shell
$ helm repo add kube-vip https://kube-vip.github.io/helm-charts
$ helm install kube-vip-cloud-provider kube-vip-cloud-provider --namespace kube-system
$ helm install kube-vip kube-vip --namespace kube-system --values values.yaml
```

## Service configuration
After everything is up and running, you can install a Service for your game server. kube-vip supports services with
mixed protocols (TCP/UDP) for ports, so we can specify all ports in one service. There are a couple of things we
need to consider here additionally.

### Annotations
First we need to annotate our service to enable the egress functionality with `kube-vip.io/egress: "true"`. If we want
to expose the server via a single static IP address, we need to add this annotation 
`kube-vip.io/loadbalancerIPs: "111.112.12.34"`,

### Service spec
We need to have a Service with `type: LoadBalancer`. If we want to have the egress functionality, we need to set
`externalTrafficPolicy: Local`.

### Example
For instance, a Service for a [Rust](https://rust.facepunch.com/) dedicated server would look like this:
```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    kube-vip.io/egress: "true"
    kube-vip.io/loadbalancerIPs: "111.112.12.34"
  labels:
    app.kubernetes.io/instance: rust-dedicated-server
    app.kubernetes.io/name: rust
  name: rust-dedicated-server
spec:
  type: LoadBalancer
  externalTrafficPolicy: Local  
  ports:
  - name: server-port
    nodePort: 30553
    port: 28015
    protocol: UDP
    targetPort: server-port
  - name: rcon-port-udp
    nodePort: 32396
    port: 28016
    protocol: UDP
    targetPort: rcon-port-udp
  - name: rcon-port-tcp
    nodePort: 32396
    port: 28016
    protocol: TCP
    targetPort: rcon-port-tcp
  - name: query-port
    nodePort: 30401
    port: 28017
    protocol: UDP
    targetPort: query-port
  - name: app-port
    nodePort: 32164
    port: 28082
    protocol: TCP
    targetPort: app-port
  selector:
    app.kubernetes.io/instance: rust-dedicated-server
    app.kubernetes.io/name: rust
```

## Check Service configuration
After installing the Service, it takes a while until kube-vip assigns the external ingress IP address and the egress
configuration. Check the logs of kube-vip-cloud-provider pods for the handling of external ingress IP address. Or
the logs of kube-vip pod for egress handling. You should see ingress IP assigned (status) and
[egress configuration](https://kube-vip.io/docs/usage/egress/#understanding-the-egress-configuration) (annotations) in
the Service object:
```shell
$ kubectl -n yournamespace get svc yourservice -o yaml 
```
