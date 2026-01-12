Title: Switching to Cilium as Container Network Interface (CNI) for my bare metal Kubernetes Clusters
Description: Making use of L2 Announcements, LB IPAM, Ingress controller and Gateway API support on Talos Linux
Summary: Making use of L2 Announcements, LB IPAM, Ingress controller and Gateway API support on Talos Linux
Date: 2026-11-02 20:00
Author: Max Pfeiffer
Lang: en
Keywords: Cilium, Kubernetes, Gateway API, L2 Announcement, LB IPAM
Image: https://max-pfeiffer.github.io/images/2025-11-30_manual-kubernetes-upgrade.png

I was looking at [Cilium](https://cilium.io/) already for quite a while and was digging through its 
[documentation](https://docs.cilium.io/en/stable/). I spotted a couple of features which are particularly useful
for bare metal Kubernetes clusters namely [L2 Announcements](https://docs.cilium.io/en/stable/network/l2-announcements/)
and [Loadbalancer IP Address Management (LB IPAM)](https://docs.cilium.io/en/stable/network/lb-ipam/).
Also it provides an [Ingress Controller](https://docs.cilium.io/en/stable/network/servicemesh/ingress/) and support
for the new [Gateway API](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/gateway-api/). Plus it
provides [Service Mesh functionality](https://docs.cilium.io/en/stable/network/servicemesh/) and an
[Egress Gatway](https://docs.cilium.io/en/stable/network/egress-gateway-toc/). All these features are implemented 
very efficiently using the eBPF Linux kernel technology. There is a good video with Thomas Graf (Co-founder of Cilium)
explaining this in more detail.

<iframe width="560" height="315" src="https://www.youtube.com/embed/80OYrzS1dCA?si=X92ijH20KOEAfhCs" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

In the past I used [MetalLB](https://metallb.io/) for providing L2 Loadbalancer and LB IPAM functionalility in my
Kubernetes clusters. With switching to [Cilium](https://cilium.io/) as CNI I can get rid of this dependency. 
I use [nginx ingress controller](https://github.com/kubernetes/ingress-nginx) in all of my clusters. Problem is 
that [nginx ingress controller is discontinued and support will already end in March 2026](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/).
Therefore, I had to take actions rather urgently and find an alternative solution for it.

## Cilium Installation
I run all my Kubernetes clusters on [Talos Linux](https://www.talos.dev/). For [Talos Linux](https://www.talos.dev/) the 
[process of installing Cilium is very well documented](https://docs.siderolabs.com/kubernetes-guides/cni/deploying-cilium).
You basically install [Cilium](https://cilium.io/) after the cluster is up and running with manifest which you add to
your machine configuration. I found it quite convenient to use [Helm](https://helm.sh/) and the
[Cilium Helm chart](https://artifacthub.io/packages/helm/cilium/cilium) to generate the manifests with `helm template`.
The configuration options and features I wanted to have I put in a `values.yaml` file. See also the
[official Cilium documentation](https://docs.cilium.io/en/stable/installation/k8s-install-helm/) for Helm installation.

For my two OpenSource Kubernetes cluster projects I used this approach with OpenTofu. You can have a look there:
* [proxmox-talos-opentofu](https://github.com/max-pfeiffer/proxmox-talos-opentofu)
* [harbor-turnkey](https://github.com/max-pfeiffer/harbor-turnkey)

## L2 Loadbalancer and LB IPAM Configuration
The L2 Loadbalancer and LB IPAM configuration is very similar to what you need to configure for
[MetalLB](https://metallb.io/). First you configure a cluster scoped
[CiliumL2AnnouncementPolicy](https://docs.cilium.io/en/stable/network/l2-announcements/#policies): 
```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumL2AnnouncementPolicy
metadata:
  name: default
spec:
  externalIPs: true
  loadBalancerIPs: true
```
And then a cluster scoped CiliumLoadBalancerIPPool:
```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: default
spec:
  blocks:
    # Configure your IP pool here
    - start: "192.168.10.95"
      stop: "192.168.10.99"
```


## Ingress Controller and Gateway API

