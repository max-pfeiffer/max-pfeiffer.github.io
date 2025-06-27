Title: Cost efficient dynamic DNS solution with AWS resources
Description: I build my own dynamic DNS solution using AWS resources and a my own dynamic-dns-update-client
Summary: I build my own dynamic DNS solution using AWS resources and a my own dynamic-dns-update-client
Date: 2025-06-27 20:00
Author: Max Pfeiffer
Lang: en
Keywords: Dynamic DNS, DNS, OpenWRT, Dynamic DNS Update Client, OpenTofu
Image: https://max-pfeiffer.github.io/blog/images/2025-03-08_overhauling_my_ceph_cluster.jpeg

For my home lab I have the need to expose some services on the public internet. And my current ISP does not offer
fixed IP addresses. So I was looking at some dynamic DNS providers out there. I did not feel like spending money on
something like this, and the free offerings look a bit shady. And I happen to already have an AWS account for running
some workloads on it. So I was exploring the Route 53 and Lambda offering a bit and saw that I can build a dynamic DNS
easily with low effort myself. And I like building stuff like that.

## Dynamic DNS server
I jumped into it and created a new project on GitHub: [Simple Dynamic DNS with AWS](https://github.com/max-pfeiffer/simple-dynamic-dns-aws)



There I created a little application which takes eats an HTTP requests with parameters containing the dynamic DNS update
data. It then configures a domain you own on AWS with Route 53 DNS service.
This application is put in a Docker container which is then run via an AWS Lambda function. That's basically it.
I want my infrastructure to be fully declarative, so I choose to provision the AWS resources with
[OpenTofu](https://opentofu.org/). This makes it also very easy to install by anyone else as you just need to pull the
repo and create your own configuration: 
```shell
$ git pull https://github.com/max-pfeiffer/simple-dynamic-dns-aws.git
$ cd dynamic-dns-update-client/opentofu
$ cp credentials.auto.tfvars.example credentials.auto.tfvars
$ vim credentials.auto.tfvars
```
And then run a couple of [OpenTofu](https://opentofu.org/) commands:
```shell
$ tofu init
$ tofu plan
$ tofu apply
```

## Dynamic DNS Client
Most consumer grade routers offer an option in their web user interface to configure updates for a dynamic DNS provider.
In a lot of cases, this is not very flexible and bound to some commercial providers that are out there. If the provider
you are using is not supported, you are screwed.
On [OpenWRT](https://openwrt.org/) routers [configuration options are plentyful](https://openwrt.org/docs/guide-user/services/ddns/client),
but configuration is a nightmare, especially if you have some more exotic use case like I have.

So I decided to write a [dynamic-dns-update-client](https://github.com/max-pfeiffer/dynamic-dns-update-client) myself.
You can run this CLI tool on an [OpenWRT](https://openwrt.org/) router or on any other machine in your infrastructure.

For installing and running [dynamic-dns-update-client](https://github.com/max-pfeiffer/dynamic-dns-update-client) on
your [OpenWRT](https://openwrt.org/) router, you need to install the Python v3 interpreter and pip. You need the
packages python3-light and python3-pip. These can be installed via Luci web interface or via SSH:
```shell
$ opkg install python3-light python3-pip
$ pip install dynamic-dns-update-client
```

You play around using the `--dry-run` option to check how it works:
```shell
$ dynamic-dns-update-client https://example.com --ip-address-url-parameter-name ip --url-parameter domain=example.com --url-parameter api-token=nd4u33huruffbn --dry-run
Current IP address: 82.4.110.122
Dry run, no changes will be made.
Dynamic DNS provider URL: https://example.com/?ip-address=82.4.110.122&domain=example.com&api-token=nd4u33huruffbn
```

If you want to use it on your [OpenWRT](https://openwrt.org/) router, I would
[add a cron job](https://openwrt.org/docs/guide-user/base-system/cron) for it. DNS entries are cached. In my experience,
an update every 10 minutes is sufficient. It's also a good idea to leverage the `--cache-ip-address` option. This
minimizes the number of HTTP requests you send to the dynamic DNS server. If you happen to use my solution, AWS is
billing you for every Lambda function run. 

So a crontab entry for an [OpenWRT](https://openwrt.org/) router would look like this:
```shell
*/10 * * * *  dynamic-dns-update-client https://example.com --ip-address-provider openwrt_network --ip-address-url-parameter-name ip --url-parameter domain=example.com --url-parameter api-token=nd4u33huruffbn --cache-ip-address

```
