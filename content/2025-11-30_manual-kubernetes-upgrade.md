Title: Upgrading Kubernetes on Debian 13 Trixie
Description: Manually upgrading a Kubernetes cluster with kubeadm
Summary: Manually upgrading a Kubernetes cluster with kubeadm
Date: 2025-11-30 12:00
Author: Max Pfeiffer
Lang: en
Keywords: Kubernetes, kubeadm, Debian
Image: https://max-pfeiffer.github.io/images/2025-11-21_manual_kubernetes-Install.png

In an [earlier article]({filename}/2025-11-21_manual_kubernetes-Install.md) I described how to install a Kubernetes
cluster manually with `kubeadm`. In this article, I will explain how to upgrade that cluster. As an operating system,
I used Debian 13 Trixie.
This process is documented in the official [Kubernetes documentation](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/).
I added some more details here that might help to do the upgrade on a Debian system.

![2025-11-30_manual-kubernetes-upgrade.png]({static}/images/2025-11-30_manual-kubernetes-upgrade.png)

## Picking the right version
First of all, you need to be aware that only upgrades between minor versions are supported. So from my current version
v1.33.5 I can only upgrade to v1.34.x. A direct upgrade to v1.35.x would not be supported. So you would need to upgrade
to v1.34.x before you could upgrade to v1.35.x. 

You need to be aware that [each minor version only gets one year of patch support](https://kubernetes.io/releases/version-skew-policy/)
nowadays. So that means that you need to upgrade your cluster at least once a year to the new minor version.

Also, you need to be aware in what order you can upgrade your cluster components on a node. This is defined in detail in
the [version skew policy documentation](https://kubernetes.io/releases/version-skew-policy/). For instance the
`kubelet` version must not be newer than the `kube-apiserver` version, so you need to upgrade the `kube-apiserver` first.

## Update Kubernetes apt repository
As a first step, you need to [upgrade your Kubernetes package repository](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/change-package-repository/)
to the new version that you would like to upgrade to. In our case, this is v1.34.1. Here we use `vim` to alter the
`/etc/apt/sources.list.d/kubernetes.list` file and add the new minor version `v1.34` and update package sources:
```shell
vim /etc/apt/sources.list.d/kubernetes.list 
apt update
```

Then we check what packages are available now:
```shell

apt list -a kubeadm
kubeadm/unknown 1.34.1-1.1 amd64 [upgradable from: 1.33.5-1.1]
kubeadm/unknown 1.34.0-1.1 amd64
kubeadm/now 1.33.5-1.1 amd64 [installed,upgradable to: 1.34.1-1.1]

kubeadm/unknown 1.34.1-1.1 arm64
kubeadm/unknown 1.34.0-1.1 arm64

kubeadm/unknown 1.34.1-1.1 ppc64el
kubeadm/unknown 1.34.0-1.1 ppc64el

kubeadm/unknown 1.34.1-1.1 s390x
kubeadm/unknown 1.34.0-1.1 s390x
```

## Update Kubernetes Components on Control Plane
Update kubeadm:
```shell
apt-mark unhold kubeadm
apt install -y kubeadm=1.34.1-1.1
apt-mark hold kubeadm
```

Verify the upgrade plan:
```shell
kubeadm upgrade plan
```

If everything looks good, upgrade the control plane:
```shell
kubeadm upgrade apply v1.34.1
```

Drain the control plane node:
```shell
kubectl drain debian-controlplane-1 --ignore-daemonsets
```

Upgrade kubelet and kubectl:
```shell
apt-mark unhold kubelet kubectl
apt install -y kubelet=1.34.1-1.1 kubectl=1.34.1-1.1
apt-mark hold kubelet kubectl
```

Restart kubelet and check the status:
```shell
systemctl daemon-reload
systemctl restart kubelet
systemctl status kubelet
```

Uncordon the control plane node and check node status:
```shell
kubectl uncordon debian-controlplane-1
kubectl get nodes
NAME                    STATUS   ROLES           AGE     VERSION
debian-controlplane-1   Ready    control-plane   24h     v1.34.1
debian-worker-1         Ready    <none>          8h      v1.33.5
debian-worker-2         Ready    <none>          6h28m   v1.33.5
```

## Upgrade Kubernetes Components on Worker Nodes
The [first two steps are the same also for worker nodes](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/upgrading-linux-nodes/)
(see above):

1. Update the Kubernetes apt repository to v1.34
2. Update kubeadm

Then upgrade the node with kubeadm:
```shell
kubeadm upgrade node
```

Then drain the node:
```shell
kubectl drain debian-worker-1 --ignore-daemonsets
```

And update kubelet:
```shell
apt-mark unhold kubelet
apt install -y kubelet=1.34.1-1.1
apt-mark hold kubelet
```

Restart kubelet and check the status:
```shell
systemctl daemon-reload
systemctl restart kubelet
systemctl status kubelet
```

Uncordon the worker node:
```shell
kubectl uncordon debian-worker-1
```

Check on the nodes:
```shell
kubectl get nodes
```
All nodes should be in status ready with the new Kubernetes version.
