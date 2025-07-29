Title: Harbor on a Kubernetes Single Node Cluster using Talos Linux and Proxmox VE
Description: I build a turn-key solution for Harbor running on a Kubernetes single node cluster using Talos Linux and Proxmox VE
Summary: I build a turn-key solution for Harbor running on a Kubernetes single node cluster using Talos Linux and Proxmox VE
Date: 2025-07-13 20:00
Author: Max Pfeiffer
Lang: en
Keywords: Harbor, Cache, Kubernetes, Talos Linux, OpenTofu, Proxmox  
Image: 

While running and maintaining my Kubernetes cluster, I was facing a chicken-egg problem:
when updating/restarting Kubernetes nodes, I hit the image pull limit of different container registries regularly.
My applications in the cluster were not coming up any more causing a lot of issues. Also I was experiencing latency
and long waiting times for pulling images from remote registries. So I was considering running some container image
cache locally.

It had to be solved outside my Kubernetes cluster because configuring an image cache is a Kubernetes node-specific
configuration depending on the container runtime and registry you use. So firing up a image cache in the already
existing Kubernetes cluster is pointless. 

I use Talos Linux for running my
Kubernetes cluster. With Talos Linux the node configuration can be done declarative and is
[straight forward and well documented](https://www.talos.dev/v1.10/talos-guides/configuration/pull-through-cache/#using-harbor-as-a-caching-registry).

I also need to 
So looking around a spotted the Harbor project. 