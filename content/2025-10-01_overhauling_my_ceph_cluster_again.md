Title: Overhauling my Ceph cluster (again)
Description: Removing Waveshare POE HATs, switching to USB power supplies    
Summary: Removing Waveshare POE HATs, switching to USB power supplies
Date: 2025-10-01 12:00
Author: Max Pfeiffer
Lang: en
Keywords: Ceph, Ceph CSI, Raspberry Pi 5
Image: https://max-pfeiffer.github.io/images/2025-10-01_overhauling_my_ceph_cluster_again_installation_done.jpeg

I already knew it when I was powering up my Ceph cluster the first time: the fans on that 
[Waveshare POE HATs (F)](https://www.waveshare.com/poe-hat-f.htm) will be a problem at some point in the future.
As there is no fan speed control in place, they are running at full throttle all the time. After running the cluster
24/7 for 10 months, the wear and tear on that fans caused a big increase in fan noise. And the Ceph cluster is placed
right next to my work place. That fan noise became worse and worse and was so annoying at some point that I decided to 
swap out the [Waveshare POE HATs (F)](https://www.waveshare.com/poe-hat-f.htm).

So I was looking at alternative POE HATs without fans first, and I found a couple on the market now. For instance, the
[Waveshare POE HAT H](https://www.waveshare.com/product/raspberry-pi/hats/interface-power/poe-hat-h.htm). But these 
are more on the pricy side. And browsing through all the new stuff on Waveshare website, I found another interesting
[HAT providing two 2.5GB ethernet ports and a NVMe SSD mount](https://www.waveshare.com/product/raspberry-pi/hats/interface-power/pcie-to-m.2-usb-eth-hat-plus.htm).
This way I could address the network throughput bottleneck I am currently facing as well. The downside of using this 
HAT would be to put the operating system on the SD-Card again, which is not optimal.

I decided to just go for USB power supplies eventually as this was the cheapest and less invasive solution I could do
at this point. I already had one Raspberry Pi 5 power supply unit and an active cooler on my shelf. So I just 
had to buy two more. Trying to place all three power supply units in my rack mounted socket strip, I noticed that these
guys need their space. So it was not possible to put all three into that socket strip because they were interfering
with each other. So I just bought another socket strip for my rack. So I ended up with this part list:

* 3x [Raspberry Pi 5 power supply](https://www.raspberrypi.com/products/27w-power-supply/)
* 3x [Raspberry Pi 5 active cooler](https://www.raspberrypi.com/products/active-cooler/)
* 1x 10'' rack mounted socket strip

![2025-09-27_overhauling_my_ceph_cluster_again_parts.jpeg]({static}/images/2025-09-27_overhauling_my_ceph_cluster_again_parts.jpeg)

## Shutting down the Ceph cluster
As a first step, I had to shut down my Ceph cluster. As I need to shut it down completely, data availability will be 
impacted. So I had to do make the consumers digest that first. You want to gracefully shut it down. Therefore, you need
to stop all running services before you shut down the machines:
```shell
cephadm shell
ceph orch stop --all
```
In practice, I noticed that a Ceph cluster is a very resilient thing and can take quite some beating. So just shutting
down single machines or all of them did no harm in my experience. I also had complete power outages, and the Ceph
cluster came up fine again.


## Installation
First I had to get rid of the bad boys: I unscrewed the Raspberry Pis and took out the noisy POE HATs.

![2025-10-01_overhauling_my_ceph_cluster_again_old_poe_hat.jpeg]({static}/images/2025-10-01_overhauling_my_ceph_cluster_again_old_poe_hat.jpeg)

Then I installed the active cooler on all devices and put it back together. 

![2025-10-01_overhauling_my_ceph_cluster_again_installation_done.jpeg]({static}/images/2025-10-01_overhauling_my_ceph_cluster_again_installation_done.jpeg)

Lastly, I put the socket strip into the 10'' rack together with the power supply units. After powering on all devices
I was checking the Ceph cluster's dashboard and was happy to see that everything was running smoothly again.
And I noticed something crucial ... silence!

## Outlook
I am not sure if I will tinker around with the Raspberrys more than I did already. There are some interesting upgrade
options that I mentioned earlier. But after looking closer at some other single board computers out there, I stumbled 
across the new [Banana PI BPI-M7](https://www.banana-pi.org/en/banana-pi-sbcs/169.html). It already comes with all 
the desired features: two 2.5GB ethernet ports, NVMe SSD adapter and more memory.
This comes with a price tag of 220 Euro for the 16GB variant at AliExpress currently. So I rather might get one of these
and try to grow my Ceph cluster with an additional Banana Pi node.