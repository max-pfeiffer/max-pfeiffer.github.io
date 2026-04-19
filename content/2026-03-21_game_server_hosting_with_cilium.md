Title: Hosting Game Servers on Bare Metal Kubernetes with Cilium as CNI  
Description: A guide for hosting dedicated game servers on Kubernetes with Cilium as CNI    
Summary: A guide for hosting dedicated game servers on Kubernetes with Cilium as CNI
Date: 2026-03-21 13:00
Author: Max Pfeiffer
Lang: en
Keywords: Game Server, UDP, Cilium, Kubernetes
Image: https://max-pfeiffer.github.io/images/2026-03-21_game_server_hosting_with_cilium.png

Last year [I switched to Cilium as CNI for my Kubernetes clusters]({filename}/2026-01-14_switching_to_cilium_cni.md).
That proved to be a very good experience in overall. And I am still very happy about the features
[Cilium](https://cilium.io/) provides and did not encounter any issues so far. As I threw out [kube-vip](https://kube-vip.io/)
and wrote an [article about UDP specifics for game server hosting with it]({filename}/2025-04-23_game_server_hosting_on_kubernetes.md),
I also want to share my experience for hosting my game servers using [Cilium](https://cilium.io/).

![2026-03-21_game_server_hosting_with_cilium.png]({static}/images/2026-03-21_game_server_hosting_with_cilium.png)

## Rust and Valheim Dedicated Game Servers
I am running [Rust](https://rust.facepunch.com/) and [Valheim](https://www.valheimgame.com/) dedicated servers.
For these game servers I created Docker images and Helm charts to run them on Kubernetes. You can check out these 
projects on GitHub. Feel free to use them:

* [rust-game-server-docker](https://github.com/max-pfeiffer/rust-game-server-docker)
* [valheim-dedicated-server-docker-helm](https://github.com/max-pfeiffer/valheim-dedicated-server-docker-helm)

[Rust](https://rust.facepunch.com/) is a rather old game, but remains extremely popular and is still in
[Steam's top 10 of most played games](https://store.steampowered.com/charts/mostplayed). I really like the survival
scenario and freedom in gameplay that [Rust](https://rust.facepunch.com/) offers.
[Valheim](https://www.valheimgame.com/) is less popular but offers a really nice and relaxed PvE experience when playing
together on your own server with a couple of friends.

With my experience using [kube-vip](https://kube-vip.io/) and [Cilium](https://cilium.io/) I shaped those two Helm 
charts so you have your game server up and running in minutes. 

## UDP Protocol
As dedicated game servers usually use UDP protocol for their client communication. [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
does not support UDP protocol only TCP. And the stable branch of Gateway API
[does not support UDPRoute](https://gateway-api.sigs.k8s.io/reference/spec/?h=udp#udproute) on the standard channel yet.
Therefore, it's pointless to utilize these [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
or [Gateway API](https://gateway-api.sigs.k8s.io/) for game server hosting.

## Cilium L2 Announcements and L2 Aware Load Balancer
When you run your Kubernetes cluster on bare metal with Cilium you usually want to make use of
[L2 Announcements and the L2 Aware load balancer](https://docs.cilium.io/en/latest/network/l2-announcements/)
as you are lacking a cloud provider's load balancer. Also, you want to use 
[Cilium's LoadBalancer IP Address Management (LB IPAM)](https://docs.cilium.io/en/stable/network/lb-ipam/).

So you typically configure a `CiliumL2AnnouncementPolicy` like this:
```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumL2AnnouncementPolicy
metadata:
  name: default
spec:
  externalIPs: true
  loadBalancerIPs: true
```
And at least one `CiliumLoadBalancerIPPool` for exposing your game servers:
```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: external
spec:
  serviceSelector:
    matchExpressions:
      - key: "lb-ip-pool"
        operator: In
        values:
          - external
  blocks:
    - start: "192.168.10.50"
      stop: "192.168.10.99"
```

## Service Configuration
For hooking up your game server to the network you need to use a [Kubernetes Service object](https://kubernetes.io/docs/concepts/services-networking/service/)
of type `LoadBalancer`. You need to configure it, so the
[Cilium IPAM load balancer](https://docs.cilium.io/en/stable/network/lb-ipam/) picks it up and assigns an external IP
address to it. 

Be aware of three Cilium peculiarities for configuring your Service:

1. `externalTrafficPolicy` needs to be set to `Cluster` [as L2 Announcements does not support `Local` as policy](https://docs.cilium.io/en/latest/network/l2-announcements/#limitations)
2. label the Service for [controlling the `CiliumLoadBalancerIPPool` selection with service selectors](https://docs.cilium.io/en/stable/network/lb-ipam/#service-selectors)
3. [annotate the Service with `lbipam.cilium.io/ips` to request a stable IP address](https://docs.cilium.io/en/stable/network/lb-ipam/#requesting-ips) for your game server

With labeling your services you can keep tight control over the IP pools you want to use for your game servers. 
And for your network routing configuration you usually need stable IP addresses of your game servers.

A full Service example could look like this for a Rust dedicated server:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: rust
  labels:
    lb-ip-pool: external
  annotations:
    lbipam.cilium.io/ips: 192.168.10.55
spec:
  type: LoadBalancer
  externalTrafficPolicy: Cluster
  ports:
    - name: server-port
      port: 28015
      targetPort: server-port
      protocol: UDP
    - name: rcon-port
      port: 28016
      targetPort: rcon-port
      protocol: TCP
    - name: query-port
      port: 28017
      targetPort: query-port
      protocol: UDP
    - name: app-port
      port: 28082
      targetPort: app-port
      protocol: TCP
  selector:
    app.kubernetes.io/name: rust
```

## Related Articles

* [Switching to Cilium as Container Network Interface (CNI) for my bare metal Kubernetes Clusters]({filename}/2026-01-14_switching_to_cilium_cni.md)
* [Hosting Game Servers on Bare Metal Kubernetes with kube-vip]({filename}/2025-04-23_game_server_hosting_on_kubernetes.md)
* [How to set up a Valheim dedicated server using Docker and Docker Compose]({filename}/2026-03-23_valheim_dedicated_server_with_docker.md)