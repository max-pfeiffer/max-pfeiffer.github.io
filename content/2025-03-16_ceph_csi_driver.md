Title: Configuring and using Ceph CSI Driver for Kubernetes
Description: A guide for configuring a Ceph cluster and Ceph CSI driver as Kubernetes storage solution   
Summary: A guide for configuring a Ceph cluster and Ceph CSI driver as Kubernetes storage solution
Date: 2025-03-16 11:00
Author: Max Pfeiffer
Lang: en
Keywords: Ceph, Ceph CSI, Container Storage Interface, Kubernetes, Storage, Volumes, PVC
Image: https://max-pfeiffer.github.io/blog/images/2025-03-16_ceph_csi_driver.png

For my Kubernetes cluster, [I build a Ceph cluster with three Raspberry PI 5 as storage solution]({filename}/2024-12-26_ceph_cluster_with_raspberry_pi_5.md). 
For hooking up that Ceph cluster to Kubernetes, you need to leverage the Kubernetes Container Storage Interface (CSI).
Kubernetes provides [an internal provisioner for Ceph Rados Block Devices (RBD)](https://kubernetes.io/docs/concepts/storage/storage-classes/#ceph-rbd).
But this provisioner is deprecated since Kubernetes v1.28. The Kubernetes team did not want to maintain it any more,
so the Ceph guys provide [Ceph CSI drivers](https://github.com/ceph/ceph-csi) for interfacing with Kubernetes nowadays. In this
article, I will explain how I configured my Ceph cluster and how I installed and configured the
[Ceph CSI drivers](https://github.com/ceph/ceph-csi) in my Kubernetes cluster.

![2025-03-16_ceph_csi_driver.png]({static}/images/2025-03-16_ceph_csi_driver.png)

Ceph provides drivers for three different file systems for Kubernetes:
[RBD](https://docs.ceph.com/en/reef/rbd/),
[CephFS](https://docs.ceph.com/en/reef/cephfs/) and
[NFS](https://en.wikipedia.org/wiki/Network_File_System).
The support for NFS is still in alpha state, so I will just focus on RBD and CephFS driver.
These two drivers support different access modes **(file mode)** for Kubernetes Volumes:

| Volume Access Mode      | Ceph CSI RBD  | Ceph CSI CephFS |
|-------------------------|---------------|-----------------|
| ReadWriteOnce (RWO)     | supported     | supported       |
| ReadOnlyMany (ROX)      | not supported | alpha state     |
| ReadWriteMany (RWX)     | not supported | supported       |
| ReadWriteOncePod (RWOP) | alpha state   | alpha state     |

Besides the **file mode** support in the table above, please be aware that only that Ceph RBD driver will give you
[**raw block** volume support for Kubernetes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#raw-block-volume-support).
Just in case you want to create some Persistent Volumes with raw block devices.

So if you want to create volumes with access mode `ReadWriteMany`, you need to install also the CephFS CSI driver in
your cluster. There is also a good video on YouTube explaining Ceph CSI drivers more in depth:

<iframe width="560" height="315" src="https://www.youtube.com/embed/kFE5C7o78Dk?si=VWGOF5tExixZ5laz" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Ceph cluster configuration
In this guide I will assume that you have access to a shell with the `ceph` command. If you installed your cluster
with `cephadm` you can quickly spawn a shell like this:
```shell
$ chephadm shell
```

### Configuration for RBD CSI Driver
The configuration for the RBD CSI driver [is well documented](https://docs.ceph.com/en/reef/rbd/rbd-kubernetes/).
You need to create a new pool and initialize it:
```shell
$ ceph osd pool create kubernetes
pool 'kubernetes' created
$ rbd pool init kubernetes
```

Then create the user for the RBD CSI driver [with these capabilities](https://github.com/ceph/ceph-csi/blob/devel/docs/capabilities.md#rbd):
```shell
$ ceph auth get-or-create client.kubernetes \
  mon 'profile rbd' \
  osd 'profile rbd pool=kubernetes' \
  mgr 'profile rbd pool=kubernetes'
[client.kubernetes]
	key = KAHDKLJDLiowejfnKjdflgmjdlfmreogkfrgmi9tmn==
```
Grab that key. You will need it later for configuring the driver.

### Configuration for CephFS CSI Driver
[Create a new CephFS file system by setting up a new volume](https://docs.ceph.com/en/reef/cephfs/#getting-started-with-cephfs):
```shell
$ ceph fs volume create cephfs
```
The [Ceph Orchestrator](https://docs.ceph.com/en/reef/mgr/orchestrator/) will do the following:

* create two new pools:
  * cephfs.cephfs.data
  * cephfs.cephfs.meta
* create a new CephFS filesystem
* create and run Metadata Servers (MDS)

We also need to create [a subvolume group](https://docs.ceph.com/en/reef/cephfs/fs-volumes/#fs-subvolume-groups).
In this subvolume group, the CephFS CSI provisioner puts the Volumes we create dynamically later.
```shell
$ ceph fs subvolumegroup create cephfs csi
```

Create a user for the CephFS CSI driver with [these capabilities](https://github.com/ceph/ceph-csi/blob/devel/docs/capabilities.md#cephfs):
```shell
$ ceph auth get-or-create client.kubernetes-cephfs \
  mgr 'allow rw' \
  osd 'allow rw tag cephfs metadata=cephfs, allow rw tag cephfs data=cephfs' \
  mds 'allow r fsname=cephfs path=/volumes, allow rws fsname=cephfs path=/volumes/csi' \
  mon 'allow r fsname=cephfs'
[client.kubernetes-cephfs]
    key = LKJUDwsdFHIeeUDHFreEUIDBNslkiedeklunUEDUEDJH==
```
Also grab that key.

## Installing Ceph CSI drivers
Ceph guys provide Helm charts for the [RBD CSI driver](https://github.com/ceph/ceph-csi/tree/devel/charts/ceph-csi-rbd)
and the [CephFS CSI driver](https://github.com/ceph/ceph-csi/tree/devel/charts/ceph-csi-cephfs). We will use these
Helm charts to install the drivers in our cluster in `csi` namespace.

When you are running a Kubernetes version, that enforces [pod security admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/),
make sure to add the `pod-security.kubernetes.io/enforce = privileged` label to that namespace. Otherwise, the
driver's pods will not come up.
```shell
$ kubectl create namespace csi
$ kubectl label namespace csi pod-security.kubernetes.io/enforce=privileged
```

Pull some more configuration information from your cluster:
```shell
$ ceph mon dump
epoch 3
fsid 4637534klj-4j44-456d-344d-348465ituhfnf
last_changed 2025-03-08T18:21:49.254139+0000
created 2025-03-08T18:09:39.262040+0000
min_mon_release 19 (squid)
election_strategy: 1
0: [v2:192.168.30.10:3300/0,v1:192.168.30.10:6789/0] mon.ceph1
1: [v2:192.168.30.11:3300/0,v1:192.168.30.11:6789/0] mon.ceph2
2: [v2:192.168.30.12:3300/0,v1:192.168.30.12:6789/0] mon.ceph3
dumped monmap epoch 3
```

### RBD CSI driver
We need to prepare our `values.yaml` file for the RBD driver installation. We insert the configuration data which
we produced in the above steps:
```yaml
csiConfig:
   - clusterID: "4637534klj-4j44-456d-344d-348465ituhfnf"
     monitors:
       - "192.168.30.10:6789"
       - "192.168.30.11:6789"
       - "192.168.30.12:6789"

storageClass:
  # Specifies whether the storageclass should be created
  create: true
  # (required) String representing a Ceph cluster to provision storage from.
  # Should be unique across all Ceph clusters in use for provisioning,
  # cannot be greater than 36 bytes in length, and should remain immutable for
  # the lifetime of the StorageClass in use.
  clusterID: "4637534klj-4j44-456d-344d-348465ituhfnf"
  # (required) Ceph pool into which the RBD image shall be created
  # (optional) if topologyConstrainedPools is provided
  # eg: pool: replicapool
  pool: "kubernetes"
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"

# Mount the host /etc/selinux inside pods to support
# selinux-enabled filesystems
selinuxMount: false

secret:
  # Specifies whether the secret should be created
  create: true
  userID: "kubernetes"
  userKey: "KAHDKLJDLiowejfnKjdflgmjdlfmreogkfrgmi9tmn=="

# Name of the configmap used for ceph.conf
cephConfConfigMapName: ceph-rbd-config
# Name of the configmap used for state
configMapName: ceph-csi-rbd-config
# Name of the configmap used for encryption kms configuration
kmsConfigMapName: ceph-csi-rbd-encryption-kms-config
```
Please not two peculiarities here:

1. With the annotation `storageclass.kubernetes.io/is-default-class: "true"` I made the RBD driver the default storage class
2. Using [Talos Linux](https://www.talos.dev/) as Kubernetes platform, I had to set `selinuxMount: false` as this was not supported
3. As we install both CSI drivers in the same namespace, we need to customize the names of the ConfigMaps

We can install the RBD CSI driver now:
```shell
$ helm repo add ceph-csi https://ceph.github.io/csi-charts
$ helm install ceph-csi-rbd ceph-csi/ceph-csi-rbd -f values.yaml --namespace csi 
```
Ceph RRB CSI driver pods should be up and running after a few seconds. Then check for their status.

### CephFS CSI driver
Also for this driver we need to prepare the `values.yaml` file:
```yaml
csiConfig:
   - clusterID: "4637534klj-4j44-456d-344d-348465ituhfnf"
     monitors:
       - "192.168.30.10:6789"
       - "192.168.30.11:6789"
       - "192.168.30.12:6789"
     cephFS:
       subvolumeGroup: "csi"

storageClass:
  # Specifies whether the storageclass should be created
  create: true
  # (required) String representing a Ceph cluster to provision storage from.
  # Should be unique across all Ceph clusters in use for provisioning,
  # cannot be greater than 36 bytes in length, and should remain immutable for
  # the lifetime of the StorageClass in use.
  clusterID: "4637534klj-4j44-456d-344d-348465ituhfnf"
  # (required) CephFS filesystem name into which the volume shall be created
  # eg: fsName: myfs
  fsName: "cephfs"

# Mount the host /etc/selinux inside pods to support
# selinux-enabled filesystems
selinuxMount: false

secret:
  # Specifies whether the secret should be created
  create: true
  adminID: "kubernetes-cephfs"
  adminKey: "LKJUDwsdFHIeeUDHFreEUIDBNslkiedeklunUEDUEDJH=="

# Name of the configmap used for ceph.conf
cephConfConfigMapName: ceph-cephfs-config
# Name of the configmap used for state
configMapName: ceph-csi-cephfs-config
# Name of the configmap used for encryption kms configuration
kmsConfigMapName: ceph-csi-cephfs-encryption-kms-config
```
Please note that we need to specify `adminID` and `adminKey` for dynamic provisioning of PersistentVolumes with this
CSI driver.

Install the CephFS driver with Helm:
```shell
$ helm repo add ceph-csi https://ceph.github.io/csi-charts
$ helm install ceph-csi-cephfs ceph-csi/ceph-csi-cephfs -f values.yaml --namespace csi 
```

## Check the results
You should have both CSI drivers up and running by now. Let's check on the installation:
```shell
$ kubectl -n csi get pods
NAME                                           READY   STATUS    RESTARTS        AGE
ceph-csi-cephfs-nodeplugin-kkkdq               3/3     Running   0               3h57m
ceph-csi-cephfs-nodeplugin-lzn79               3/3     Running   0               3h57m
ceph-csi-cephfs-nodeplugin-w4qpl               3/3     Running   0               3h57m
ceph-csi-cephfs-provisioner-58744fdf76-59dnk   5/5     Running   0               3h57m
ceph-csi-cephfs-provisioner-58744fdf76-66rzk   5/5     Running   0               3h57m
ceph-csi-cephfs-provisioner-58744fdf76-tslzf   5/5     Running   3 (3h55m ago)   3h57m
ceph-csi-rbd-nodeplugin-8vz7g                  3/3     Running   0               3h57m
ceph-csi-rbd-nodeplugin-bhpqh                  3/3     Running   0               3h57m
ceph-csi-rbd-nodeplugin-nxkfz                  3/3     Running   0               3h57m
ceph-csi-rbd-provisioner-bd78f48fd-2g9nf       7/7     Running   3 (3h55m ago)   3h57m
ceph-csi-rbd-provisioner-bd78f48fd-ht8tc       7/7     Running   0               3h57m
ceph-csi-rbd-provisioner-bd78f48fd-l2kc2       7/7     Running   0               3h57m

$ kubectl get storageclass                     
NAME                   PROVISIONER           RECLAIMPOLICY   VOLUMEBINDINGMODE   ALLOWVOLUMEEXPANSION   AGE
csi-cephfs-sc          cephfs.csi.ceph.com   Delete          Immediate           true                   3h57m
csi-rbd-sc (default)   rbd.csi.ceph.com      Delete          Immediate           true                   3h57m
```
Pods of the CSI drivers should now be running in `csi` namespace, and you should have two StorageClasses available.
Let's create a PersistentVolumeClaim with each of the StorageClasses:
```shell
$ cat <<EOF > test-rbd-pvc.yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-rbd-pvc
spec:
  accessModes:
    - ReadWriteOnce
  volumeMode: Filesystem
  resources:
    requests:
      storage: 1Gi
  storageClassName: csi-rbd-sc
EOF
$ kubectl apply -f test-rbd-pvc.yaml
$ kubectl get pvc test-rbd-pvc      
NAME           STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
test-rbd-pvc   Bound    pvc-dbb3d97e-eab5-45b9-81e9-3140eadc8a49   1Gi        RWO            csi-rbd-sc     <unset>                 20s
```
If the PVC became bound, we are good.

Let's check if it also works with the CephFS StorageClass:
```shell
$ cat <<EOF > test-cephfs-pvc.yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-cephfs-pvc
spec:
  accessModes:
    - ReadWriteMany
  volumeMode: Filesystem
  resources:
    requests:
      storage: 1Gi
  storageClassName: csi-cephfs-sc
EOF
$ kubectl apply -f test-cephfs-pvc.yaml
$ kubectl get pvc test-cephfs-pvc      
NAME              STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS    VOLUMEATTRIBUTESCLASS   AGE
test-cephfs-pvc   Bound    pvc-cd5c3d81-9596-4a44-9f11-250fa30ad152   1Gi        RWO            csi-cephfs-sc   <unset>                 3s
```
When this PVC also became bound, we are happy campers. Now you can use these two new StorageClasses for applications
you run in your Kubernetes cluster.

## Related Articles

* [Ceph Cluster with Raspberry Pi 5 and NVMe SSDs]({filename}/2024-12-26_ceph_cluster_with_raspberry_pi_5.md) 
* [Overhauling my Ceph cluster ]({filename}/2025-05-10_overhauling_my_ceph_cluster.md)
