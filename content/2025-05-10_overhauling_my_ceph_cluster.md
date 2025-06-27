Title: Overhauling my Ceph cluster 
Description: Upgrading all Raspberry Pi 5 with NVMe HAT supporting two SSDs, re-installing Ceph cluster, Vlan configuration    
Summary: Upgrading all Raspberry Pi 5 with NVMe HAT supporting two SSDs, re-installing Ceph cluster, Vlan configuration
Date: 2025-05-10 12:00
Author: Max Pfeiffer
Lang: en
Keywords: Ceph, Ceph CSI, Raspberry Pi 5, VLAN, Kubernetes
Image: https://max-pfeiffer.github.io/blog/images/2025-05-10_overhauling_my_ceph_cluster.jpeg

I decided to optimize and secure my network setup at home. As part of this new configuration, I decided to put my Ceph
cluster into a separate network and use a VLAN. After reading the
[official documentation on that topic](https://docs.ceph.com/en/latest/rados/operations/add-or-rm-mons/#changing-a-monitor-s-ip-address),
I learned that I am starting some bigger endeavour here. According to the documentation, existing Ceph monitors are not
supposed to change their IP addresses. 😀 Nonetheless, I gave that a shot and screwed up my Ceph clusters
configuration eventually. Not to a point where I could not fix it, but at some point I choose to reinstall the Ceph
cluster because that seemed to be less work.

Also, I was not fully satisfied with the hardware setup of my devices: I was running the operating system for the
Raspberry Pis on SD cards. When I put this together, this was an inexpensive and convenient option.
This worked fine for roughly six months since
[I initially put that together]({filename}/2024-12-26_ceph_cluster_with_raspberry_pi_5.md). But that was
not a speedy option for storing the monitor's map on the devices. Also, I am worried about the wear and tear on the SD
Cards. So I choose to also improve the hardware setup and rip apart my Ceph cluster completely.

## Hardware Improvements
I choose to go for another NVMe SSD for the Raspberry Pis main system storage. Therefore, I had to swap out the existing
NVMe HAT I currently use for the devices as it just supports a single NVME SSD. So I ended up with this part list:

* [3x Waveshare PCIe To 2-Ch M.2 Adapter Type B](https://www.waveshare.com/pcie-to-2-ch-m.2-hat-plus-b.htm)
* [3x Transcend 110S NVMe SSD](https://www.transcend-info.com/product/internal-ssd/mte110s-112s)

I removed the existing NVME HATs from all devices and installed the new one with two NVMe SSDs.

![2025-03-08_overhauling_my_ceph_cluster.jpeg]({static}/images/2025-05-10_overhauling_my_ceph_cluster.jpeg)

## Re-installing the Ceph Cluster
### Installing the Operating System
With the [Raspberry Pi Imager](https://github.com/raspberrypi/rpi-imager) I flashed the Ubuntu server v24.04 to the
three NVMe SSDs. I used a
[NVMe adapter from LogiLink](https://www.2direct.de/computer/festplattengehaeuse-zubehoer/dockingstations/5370/usb-3.2-gen2-quickport-1-port-fuer-m.2-nvme-pcie-und-sata-ngff-ssds)
to do that. 

### Installing Ceph
I will not go too much into the details for the Ceph cluster installation itself as I already was covering this in my
[earlier article about the initial installation]({filename}/2024-12-26_ceph_cluster_with_raspberry_pi_5.md).
So let's assume we already installed the Ceph cluster using `cephadm` and we would like to add the old devices for this
cluster.

Enter a shell using cephadm and check the old devices' status:
```shell
$ cephadm shell
$ ceph orch device ls --wide --refresh
HOST   PATH          TYPE  TRANSPORT  RPM  DEVICE ID                              SIZE  HEALTH  IDENT  FAULT  AVAILABLE  REFRESHED  REJECT REASONS                                                           
ceph1  /dev/nvme0n1  ssd                   KINGSTON_SNV3S1000G_50026B73831D5E2F   931G          N/A    N/A    No         6m ago     Has a FileSystem, Insufficient space (<10 extents) on vgs, LVM detected  
ceph2  /dev/nvme0n1  ssd                   KINGSTON_SNV3S1000G_50026B7785C1AC00   931G          N/A    N/A    No         6m ago     Has a FileSystem, Insufficient space (<10 extents) on vgs, LVM detected  
ceph3  /dev/nvme0n1  ssd                   KINGSTON_SNV3S1000G_50026B7785C1ABFC   931G          N/A    N/A    No         6m ago     Has a FileSystem, Insufficient space (<10 extents) on vgs, LVM detected
```

The old clutter is still on the devices. So we need to zap the SSDs on all hosts:
```shell
$ ceph orch device zap ceph1 /dev/nvme0n1 --force
zap successful for /dev/nvme0n1 on ceph1
$ ceph orch device zap ceph2 /dev/nvme0n1 --force
zap successful for /dev/nvme0n1 on ceph2
$ ceph orch device zap ceph3 /dev/nvme0n1 --force
zap successful for /dev/nvme0n1 on ceph3
$ ceph orch device ls --wide --refresh
HOST   PATH          TYPE  TRANSPORT  RPM  DEVICE ID                              SIZE  HEALTH  IDENT  FAULT  AVAILABLE  REFRESHED  REJECT REASONS  
ceph1  /dev/nvme0n1  ssd                   KINGSTON_SNV3S1000G_50026B73831D5E2F   931G          N/A    N/A    Yes        3m ago                     
ceph2  /dev/nvme0n1  ssd                   KINGSTON_SNV3S1000G_50026B7785C1AC00   931G          N/A    N/A    Yes        3m ago                     
ceph3  /dev/nvme0n1  ssd                   KINGSTON_SNV3S1000G_50026B7785C1ABFC   931G          N/A    N/A    Yes        3m ago                     
```

Add all SSDs as storage devices to the Ceph cluster:
```shell
$ ceph orch apply osd --all-available-devices
Scheduled osd.all-available-devices update...
```

After a while, I checked my Ceph dashboard: all devices were added. The cluster was healthy and operational again.
In my Kubernetes cluster, I just had to update the [Ceph CSI driver configuration]({filename}/2025-03-16_ceph_csi_driver.md)
with the new Ceph cluster information:

* IP addresses of Ceph monitors
* Cluster ID
* secrets

Then everything was operational again.

## Observations
The main bottleneck of my setup is the networking. A Raspberry Pi 5 just has a Gigabit network adapter. So throughput
is limited to just ~100MB per second. With jumbo frames, you can tease out more throughput. But this has undesirable 
side effects in this setup in conjunction with Kubernetes.
This is ok for some lab environment you run at home. But this is absolutely not sufficient for more serious appliances.
I guess I do not need to tell you that using Raspberry Pis for a Ceph cluster is not a good idea for any serious
appliance at all. 😀

## Related Articles

* [Ceph Cluster with Raspberry Pi 5 and NVMe SSDs]({filename}/2024-12-26_ceph_cluster_with_raspberry_pi_5.md) 
* [Configuring and using Ceph CSI Driver for Kubernetes]({filename}/2025-03-16_ceph_csi_driver.md)


