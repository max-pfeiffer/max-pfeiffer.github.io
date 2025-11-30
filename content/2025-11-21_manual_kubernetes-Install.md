Title: Installing Kubernetes on Debian 13 Trixie
Description: Manually installing a Kubernetes cluster with kubeadm
Summary: Manually installing a Kubernetes cluster with kubeadm
Date: 2025-11-21 18:00
Author: Max Pfeiffer
Lang: en
Keywords: Kubernetes, kubeadm, Debian
Image: https://max-pfeiffer.github.io/images/2025-11-21_manual_kubernetes-Install.png

I am currently preparing for the Kubernetes administrator certification ([CKA](https://www.cncf.io/training/certification/cka/)).
As an exercise, I was already setting up
[Kubernetes the hard way](https://github.com/kelseyhightower/kubernetes-the-hard-way). Thanks to Kelsey Hightower 
who provided that great tutorial to the community. That was a very good experience, and I learned a lot about the
Kubernetes bootstrapping process.

But I need some more practice with `kubeadm` for doing the certification, so I choose to bootstrap a Kubernetes
cluster with that tooling as well. The process is documented quite well [in the official Kubernetes documentation](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/).
I wrote this article mainly to capture my learning. I found some more background information that I added here
so that article provides a bit more value than the official documentation. Also, I added some more details on how to
practically do the installation on a Debian system.

I manually provisioned three virtual machines with Debian 13. One for a control plane and the other two for worker nodes.
[Kubernetes nodes can be configured to utilize swap memory, but that comes with some caveats.](https://kubernetes.io/docs/concepts/cluster-administration/swap-memory-management/)
If you don't plan to use swap memory later, you can provision your virtual machines without swap in the first place.
Then you don't need to switch it off later.

Here I install with v1.33.5 an older version of Kubernetes. The reason for this is that I would like to upgrade that
cluster manually with `kubeadm` at some later point. So if you want to install a cluster running the latest Kubernetes,
[check for the latest release](https://github.com/kubernetes/kubernetes/releases) and use that version.

![2025-11-21_manual_kubernetes-Install.png]({static}/images/2025-11-21_manual_kubernetes-Install.png)

## Control Plane
Pick one of the three virtual machines to be your control plane.

### Turn Swap off
If you happen to have swap enabled on your node, you need to disable it first.
[The default behavior of a kubelet is to fail to start if swap memory is detected on a node.](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/#swap-configuration)
We switch it off by masking the swap unit using systemctl:
```shell
$ swapon --show
NAME      TYPE      SIZE USED PRIO
/dev/sda5 partition 1.7G   0B   -2

$ systemctl list-units --type swap
  UNIT                                                                      LOAD   ACTIVE SUB    DESCRIPTION                                           
  dev-disk-by\x2duuid-62a3642e\x2db966\x2d46b4\x2dbb58\x2de453f240e351.swap loaded active active /dev/disk/by-uuid/62a3642e-b966-46b4-bb58-e453f240e351

Legend: LOAD   → Reflects whether the unit definition was properly loaded.
        ACTIVE → The high-level unit activation state, i.e. generalization of SUB.
        SUB    → The low-level unit activation state, values depend on unit type.

1 loaded units listed. Pass --all to see loaded but inactive units, too.
To show all installed unit files use 'systemctl list-unit-files'.

$ systemctl mask 'dev-disk-by\x2duuid-62a3642e\x2db966\x2d46b4\x2dbb58\x2de453f240e351.swap'
Created symlink '/etc/systemd/system/dev-disk-by\x2duuid-62a3642e\x2db966\x2d46b4\x2dbb58\x2de453f240e351.swap' → '/dev/null'.
```
Reboot the machine, then check again for swap:
```shell
swapon --show
```
Swap should be turned off now.

### Enable IPv4 packet forwarding
I will use [Cilium](https://cilium.io/) as CNI for this Kubernetes cluster.
Reading through the [Cilium documentation](https://docs.cilium.io/en/stable/network/concepts/routing/)
and [Kubernetes documentation](https://kubernetes.io/docs/setup/production-environment/container-runtimes/#prerequisite-ipv4-forwarding-optional)
I came to the conclusion that enabling the IPv4 packet forwarding might not be needed as [Cilium](https://cilium.io/)
takes care of it on its own behalf. But during installation I noticed that `kubeadm` is actually checking for this 
setting in its pre-flight checks before installation. So you need to add it at this point.

First load kernel drivers to make sure they are present before changing the config:
```shell
modprobe overlay
modprobe br-netfilter
```
Then apply new kernel parameters:
```shell
# sysctl params required by setup, params persist across reboots
cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
EOF
# Apply sysctl params without reboot
sysctl --system
```
Check if changes were persisted:
```shell
$ sysctl net.ipv4.ip_forward
net.ipv4.ip_forward = 1
$ sysctl net.bridge.bridge-nf-call-ip6tables
net.bridge.bridge-nf-call-ip6tables = 1
$ sysctl net.bridge.bridge-nf-call-iptables
net.bridge.bridge-nf-call-iptables = 1
```

### Debian Packages
Install the needed Debian packages:
```shell
apt update
apt install -y ca-certificates curl gpg socat conntrack ipset kmod vim
```

### Install Containerd
We need to install [containerd](https://containerd.io/) as [container runtime](https://kubernetes.io/docs/setup/production-environment/container-runtimes/) first.
Make sure to install a [compatible version of containerd for your Kubernetes version](https://containerd.io/releases/#kubernetes-support).

[Setup Docker apt repository for installing containerd](https://docs.docker.com/engine/install/debian/#install-using-the-repository):
```shell
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
```
Install containerd:
```shell
apt install containerd.io
```
Now we need to create and modify the config. There are two configuration changes we need to consider:

1. [We need to use the systemd cgroup driver in /etc/containerd/config.toml with runc.](https://kubernetes.io/docs/setup/production-environment/container-runtimes/#containerd-systemd)
2. [Update the reference for the sandbox pause image](https://kubernetes.io/docs/setup/production-environment/container-runtimes/#override-pause-image-containerd)

```shell
containerd config default | tee /etc/containerd/config.toml
sed -e 's/SystemdCgroup = false/SystemdCgroup = true/g' -i /etc/containerd/config.toml
```

You can use `vim` to edit `/etc/containerd/config.toml` and set it to the up-to-date version.

Then restart containerd and check its status:
```shell
systemctl restart containerd
systemctl status containerd
```

### Install Helm
Install the Kubernetes package manager [Helm](https://helm.sh/):
```shell
curl -fsSL https://packages.buildkite.com/helm-linux/helm-debian/gpgkey | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/helm.gpg] https://packages.buildkite.com/helm-linux/helm-debian/any/ any main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
apt update
apt install helm
```

### Install Kubernetes
We will install Kubernetes now. It's recommended to use the [community owned package repositories](https://kubernetes.io/blog/2023/08/15/pkgs-k8s-io-introduction/).
You need to add them as they are not available on Debian be default. So we add the v1.33 Kubernetes apt repository: 
```shell
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
apt update
```
Install kubeadm, kubelet and kubectl:
```shell
apt install -y kubeadm=1.33.5-1.1 kubelet=1.33.5-1.1 kubectl=1.33.5-1.1
```
Pin the versions for kubeadm, kubelet and kubectl to prevent accidental upgrades:
```shell
apt-mark hold kubelet kubeadm kubectl
```

If you assigned a static IP to you machine, Debian by default already added an entry for it in `/etc/hosts`.
For instance:
```shell
192.168.20.210	debian-controlplane-1.lan	debian-controlplane-1
```
Modify `/etc/hosts` and add an entry for the control plane endpoint:
```shell
echo "$(hostname -i)  debian-k8s-endpoint" >> /etc/hosts
```
Add also the other two worker nodes. So it looks like this eventually:
```shell
192.168.20.210	debian-controlplane-1.lan	debian-controlplane-1
[...]
# Kubernetes
192.168.20.210  debian-k8s-endpoint
192.168.20.211	debian-worker-1.lan	debian-worker-1
192.168.20.212	debian-worker-2.lan	debian-worker-2
```

[Initialize the control plane node](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/#initializing-your-control-plane-node):
```shell
kubeadm init --kubernetes-version 1.33.5 --control-plane-endpoint debian-k8s-endpoint
```

### Configure kubectl for non-root user
Switch to your regular non-root user and configure admin access for kubectl (see also `kubeadm init` output):
```shell
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```
Check on your node:
```shell
$ kubectl get nodes
NAME                    STATUS     ROLES           AGE     VERSION
debian-controlplane-1   NotReady   control-plane   5m56s   v1.33.5
```

### Install Cilium as CNI
Install [Cilium](https://cilium.io/) CNI using helm:
```shell
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.18.3 --namespace kube-system
```
You can [check connectivity with Cilium tooling](https://docs.cilium.io/en/stable/installation/k8s-install-helm/#validate-the-installation).

## Worker Nodes
Now we can add additional worker nodes. On each worker node we need to prepare the node (see above):

1. Switch off swap (if needed)
2. Enable packet forwarding (if needed)
3. Install Debian packages
4. Install containerd
5. Add Kubernetes apt repository

We do not need to install kubectl and Helm.

### Install Kubernetes
Install kubeadm and kubelet:
```shell
KUBERNETES_VERSION=1.33.5-1.1
apt install -y kubeadm=$KUBERNETES_VERSION kubelet=$KUBERNETES_VERSION
```
Pin the versions for kubeadm and kubelet to prevent accidental upgrades:
```shell
apt-mark hold kubelet kubeadm kubectl
```

### Add Host Entries
You can check your nodes IP address with `hostname -i`.
Add all host entries to `/etc/hosts` also on this node.
```shell
# Kubernetes
192.168.20.210  debian-k8s-endpoint
192.168.20.211	debian-worker-1.lan	debian-worker-1
192.168.20.212	debian-worker-2.lan	debian-worker-2
```

### Join the Worker Node
On the control plane node issue a new token and print the join command:
```shell
$ kubeadm token create --print-join-command
kubeadm join debian-k8s-endpoint:6443 --token 7dvrku.gk93a26j6o0maiwn --discovery-token-ca-cert-hash sha256:61d474bef805e9c8d14d3ac96a80e5b2031d7b06fecd9296b4aa77ba15755892 
```
On the worker node use that generated join command to join that node to the cluster:
```shell
kubeadm join debian-k8s-endpoint:6443 --token 7dvrku.gk93a26j6o0maiwn --discovery-token-ca-cert-hash sha256:61d474bef805e9c8d14d3ac96a80e5b2031d7b06fecd9296b4aa77ba15755892 
```
Watch the console output. After a while check on the control plane node for the nodes:
```shell
$ kubectl get nodes
NAME                    STATUS     ROLES           AGE   VERSION
debian-controlplane-1   Ready      control-plane   15h   v1.33.5
debian-worker-1         Ready      <none>          17s   v1.33.5
```

## Additional Control Plane and Worker Nodes
If you want to add additional control plane or worker nodes, just add a new machine as described above for any
additional node. Please be aware that you need to add `--control-plane` as an option when you want to join a control
plane node with `kubeadm join`.

When you work with virtual machines on a hypervisor, you probably want to make use of templates to ease your work here.
I was doing this just for the sake of getting some practice with `kubeadm`. 
