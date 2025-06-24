Title: Ceph Cluster with Raspberry Pi 5 and NVMe SSDs
Description: Bare metal provisioning of a Ceph cluster with three Raspberry Pi 5 and NVMe SSDs 
Summary: Bare metal provisioning of a Ceph cluster with three Raspberry Pi 5 and NVMe SSDs
Date: 2024-12-26 10:00
Author: Max Pfeiffer
Lang: en
Keywords: Ceph, Raspberry Pi, NVMe, SSD
Image: https://max-pfeiffer.github.io/blog/images/2024-12-26_ceph_cluster.jpeg

As described in an earlier article, I run a Kubernetes cluster on my
[Proxmox VE hypervisor](https://www.proxmox.com/en/proxmox-virtual-environment/overview) using Talos Linux. For this
Kubernetes cluster I built a [Ceph](https://ceph.io/) cluster as a storage solution. This time I did not want to do this
with virtual machines using my Hypervisor. I choose to set it up on bare metal in order to learn a bit how
[Ceph](https://ceph.io/) deals with hardware and different storage devices. Doing this, I ran into some bugs during Ceph
installation and provisioning the [Ceph CSI](https://github.com/ceph/ceph-csi) on the Kubernetes cluster. So I decided
to share my experience with it. I might help someone out there and save him some time.

[Proxmox VE hypervisor](https://www.proxmox.com/en/proxmox-virtual-environment/overview) offers its own
[Ceph cluster solution](https://pve.proxmox.com/wiki/Deploy_Hyper-Converged_Ceph_Cluster). But this is geared towards
providing storage pools for virtual machines on that hypervisor. It also just deploys one
[Ceph monitor](https://docs.ceph.com/en/reef/glossary/#term-Ceph-Monitor) per hypervisor host. The
[Ceph monitor](https://docs.ceph.com/en/reef/glossary/#term-Ceph-Monitor) maintains a map of the state of the cluster.
You need at least three monitors in order to be redundant and highly available. So if you have only one Promox VE
server running (like me), this is not a good option. Plus that Ceph installation is tightly coupled and
intermingled with Proxmox VE. So tinkering with that configuration and cluster authentication was causing problems
when I tried it out.

## Hardware
I choose to use Raspberry Pi 5 as a platform because they have enough computing power and RAM for a small lab cluster
with little usage/traffic. Since a while these add on HATs for NVMe SSDs are available for it, so I thought that
could be a speedy and affordable way to handle storage. I basically threw all of this then in a 10'' desktop rack
together with a POE switch.

![Ceph Cluster in 10'' rack]({static}/images/2024-12-26_ceph_cluster.jpeg)

Parts list:

* [DeskPi RackMate T1 Rackmount 10''](https://deskpi.com/products/deskpi-rackmate-t1-2)
* [Ubiquiti Es-8-150w POE Switch](https://store.ui.com/us/en/products/es-8-150w)
* 3x [Raspberry Pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/)
* 3x [Waveshare POE HAT (F)](https://www.waveshare.com/poe-hat-f.htm)
* 3x [Waveshare PCIe To M.2 Adapter Board (D)](https://www.waveshare.com/pcie-to-m.2-board-d.htm)
* 3x [SanDisk Extreme microSDXC, 64 GB, U3, UHS-I](https://www.digitec.ch/en/s1/product/sandisk-extreme-microsdxc-microsdxc-64-gb-u3-uhs-i-memory-card-20932252)
* 3x [Kingston NV3 NVMe SSD 1000GB](https://www.kingston.com/en/ssd/nv3-nvme-pcie-ssd)

## Installing Ubuntu on Raspberry Pis
Checking on the [OS recommendations for Ceph](https://docs.ceph.com/en/reef/start/os-recommendations/) I learned that
Ubuntu should be a good option: Ubuntu 22.04 was tested with Ceph v18.2.
The problem is that for Raspberry Pi 5 only Ubuntu 24.04 is available. Ubuntu 22.04 will not be backported for
Raspberry Pi 5. So I flashed Ubuntu 24.04 onto the micro SD cards using the [Raspberry Pi imager](https://www.raspberrypi.com/software/).
I found it quite usefully to use the customization options of Raspberry Pi imager and provision hostnames and SSH keys
when flashing the images.

### The Cephadm Bug in v19.2.0
[The recommended installation method is nowadays cephadm.](https://docs.ceph.com/en/reef/install/#recommended-methods)
I noticed that only Docker was missing from [requirements](https://docs.ceph.com/en/reef/cephadm/install/#requirements)
after installing Ubuntu. So I quickly installed it on all nodes:

    :::shell
    apt update
    apt install docker.io

You need to pick one of the Raspberry Pis to be your admin node. Then you just
[install cephadm](https://docs.ceph.com/en/reef/cephadm/install/#install-cephadm) on that node.  I choose to install
the ubuntu package for simplicity:

    ::shell
    apt install cephadm

That installs the v19.2.0 version on Ubuntu 24.04 currently. But that version is not tested with this Ubuntu version
(see above), and this is a problem. 😀 So there is a [bug in the v19.2.0 cephadm version](https://tracker.ceph.com/issues/66389),
where it is not able to parse AppArmor profiles in `/sys/kernel/security/apparmor/profiles`. This will cause you a
multitude of problems: storage devices will not become discovered, cluster communication is flawed etc.. Please check
on [the Stackoverflow thread](https://stackoverflow.com/questions/78743144/ceph-faild-to-add-osd-node-to-a-new-ceph-cluster-error-einval-traceback-most)
for more details. The [fix](https://tracker.ceph.com/issues/66530) is already on its way for cephadm v19.2.1.

Besides cephadm I choose not to install additional ceph packages (i.e., ceph, ceph-volume), as you can run almost any
admin command with `cephadm shell`.

### The Workaround
As this problem is caused by the MongoDB Compass profile containing spaces in the name, I choose to disable that
Apparmor profile as workaround. I am not using MongoDB on the machines, so this should not be a problem. You need to
apply the workaround on all Raspberry Pis:

    ::shell
    sudo ln -s /etc/apparmor.d/MongoDB_Compass /etc/apparmor.d/disable/
    sudo apparmor_parser -R /etc/apparmor.d/MongoDB_Compass
    sudo systemctl reload apparmor.service

Check that the MongoDB_Compass profile became disabled:

    ::shell
    sudo systemctl status apparmor.service
    sudo cat /sys/kernel/security/apparmor/profiles | grep MongoDB

## Boostrap Ceph cluster
[Bootstrapping the Ceph Cluster with cephadm](https://docs.ceph.com/en/reef/cephadm/install/#bootstrap-a-new-cluster)
on your admin node is straight forward, the IP address is the one of your admin node:

    ::shell
    cephadm bootstrap --mon-ip 192.168.1.100

## Adding Hosts
My node layout looks like this:

* hostname: ceph1, IP: 192.168.1.100, admin node 
* hostname: ceph2, IP: 192.168.1.101
* hostname: ceph3, IP: 192.168.1.102

Cephadm needs a user which needs a certain set of permissions. By default, the root user is used, but
[you can also configure a different user with narrowed down permissions](https://docs.ceph.com/en/octopus/cephadm/operations/#configuring-a-different-ssh-user).
I am just going with the default here.

In order to add the other two nodes, you need to configure the sshd in `/etc/ssh/sshd_config` and permit root login:
`PermitRootLogin yes` or better `PermitRootLogin prohibit-password`. After that, you can copy over the SSH keys from the
admin node like that:

    ::shell
    ssh-copy-id -f -i /etc/ceph/ceph.pub root@ceph2
    ssh-copy-id -f -i /etc/ceph/ceph.pub root@ceph3
    
[Add the hosts like this](https://docs.ceph.com/en/reef/cephadm/host-management/#adding-hosts):

    ::shell
    sudo cephadm shell ceph orch host add ceph2 192.168.1.101
    sudo cephadm shell ceph orch host add ceph3 192.168.1.102

On these two nodes Ceph will add a monitor each, so you then have in total three monitors and a highly available Ceph
cluster.

## Adding Devices and Object Storage Daemons (OSD)
Please be aware that you can only add new devices if these
[requirements](https://docs.ceph.com/en/reef/cephadm/services/osd/#listing-storage-devices) are met:

* The device must have no partitions.
* The device must not have any LVM state.
* The device must not be mounted.
* The device must not contain a file system. 
* The device must not contain a Ceph BlueStore OSD. 
* The device must be larger than 5 GB.

So you better check if this is actually the case:

    ::shell
    sudo cephadm shell ceph orch device ls --wide --refresh

If there is a problem, you will see that listed in the `REJECT REASONS` column. You might need to follow up on that by
using fdisk to remove partitions or using `ceph-volume lvm zap` to clean up devices.
I had no problems adding my three NVMe SSDs on the three Raspberry Pis.

If everything looks fine, you can just add all storage devices and create the ODS in one go:

    ::shell
    sudo cephadm shell ceph orch apply osd --all-available-devices

## Checking Result
Everything should be up and running by now. You can check the results in the web dashboard which runs on the admin
node: [https://ceph1:8443/](https://ceph1:8443/)

![Ceph Dashboard]({static}/images/2024-12-26_ceph_dashboard.png)

## Self-Criticism
Working on the project, I noticed already some things I need to improve. Having the operating system running on the
SD cards was probably not the best idea. Especially the monitors will cause some serious wear and tear there. So I
probably need to change that at some point in the future. So I already eyeballed other PCIe to M.2 adapters which
support more than one SSD like [this one](https://www.waveshare.com/pcie-to-2-ch-m.2-hat-plus-b.htm). That way I could
have one SSD for the operating system and one for storage.
I admit that the managed 150W POE switch is quite overkill for that project. But I choose that one because I also
want to use it for other lab projects in the future. There are many cheaper options out there. For instance, Waveshare
is offering this [cheap 120W POE switch](https://www.waveshare.com/gigabit-poe-switch-120w.htm) which would fully
suffice for that project.
Also, that DeskPi Rackmount is rather pricy for what it offers. So if you find cheaper options, I would rather go with
this.

## Outlook
I will do a follow-up post on that topic for configuring the [Ceph CSI](https://github.com/ceph/ceph-csi) for the
Kubernetes cluster as this proved not to be that straight forward.
I already threw in some hard drives in my Proxmox machine and plan to set up another Ceph cluster there. I am interested
to do some performance comparison between these two Ceph clusters.

## Related Articles

* [Configuring and using Ceph CSI Driver for Kubernetes]({filename}/2025-03-16_ceph_csi_driver.md)
* [Overhauling my Ceph cluster ]({filename}/2025-05-10_overhauling_my_ceph_cluster.md)
