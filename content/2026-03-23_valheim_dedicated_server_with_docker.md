Title: How to set up a Valheim dedicated server using Docker and Docker Compose 
Description: A guide for setting up your own Valheim dedicated server using Docker and Docker Compose    
Summary: A guide for setting up your own Valheim dedicated server using Docker and Docker Compose
Date: 2026-03-23 20:00
Author: Max Pfeiffer
Lang: en
Keywords: Valheim, dedicated server, Docker
Image: https://max-pfeiffer.github.io/images/2026-03-23_valheim_dedicated_server_with_docker.png

I enjoy playing [Valheim](https://www.valheimgame.com/) from while to while. It offers a very nice and relaxed PvE
experience when playing together with a couple of friends.
For this game it really makes sense to run your own server as you can control the world you play in and you
have that game open 24/7 to everyone who wants to join playing.

![2026-03-23_valheim_dedicated_server_with_docker.png]({static}/images/2026-03-23_valheim_dedicated_server_with_docker.png)

## Docker Image
The guys from Iron Gate Studios actually did a very good job in providing the community with a 
[Valheim dedicated server guide](https://www.valheimgame.com/support/a-guide-to-dedicated-servers/).
And they even provide a Docker setup in their Steam distribution. So you could just follow this and you are set.

However I found that setup they are suggesting a bit labor intensive to maintain in the long run. I did not feel
like tinkering around with the server setup after every software update: building a new Docker image, adapting that
new image and restart the server using this new image. This would also mean to have a longer server downtime.

Another problem with that approach from Iron Gate Studios is, that the Valheim server is run with root user in that
image. I also wanted to improve that from the security perspective.

So I choose to [build my own image on GitHub](https://github.com/max-pfeiffer/valheim-dedicated-server-docker-helm)
and automate that using [GitHub actions](https://github.com/features/actions). That way I am able to check for a 
Valheim server update and build an image every day. This makes it possible to use the `latest` tag of that image as 
it is always up-to-date. If you use the `latest` tag together with `pull_policy: always` in your docker compose file, 
you can easily automate that server update using a shell script and a cron job.

## Docker Volume
Another detail that you need to be aware of is that the Valheim dedicated server is a 
[stateful application](https://glossary.cncf.io/stateful-apps/) by design as it stores player and world data in the
file system. You can control the file system location with `-savedir` CLI option.

When you run an application in a Docker container the files in the Docker container are only persisted inside the container 
as long as the container exists. So if you run a new Docker container with a new Valheim server version, all files
in your `-savedir` location are gone. This is not what we want because we would loose all world and player data.

With a [Docker Volume](https://docs.docker.com/storage/volumes/) you can overcome that issue. This enables you to persist the Valheim server data when
you switch to new Docker images with new Valheim server versions. You need to mount that [Docker Volume](https://docs.docker.com/storage/volumes/)
on your `-savedir` location. This way you make sure your data is still there. That data lives until you delete
the [Docker Volume](https://docs.docker.com/storage/volumes/).

## Docker Compose
The Docker way to pull all this together is [Docker Compose](https://docs.docker.com/compose/). With a docker compose
file you can define your Valheim server service and the [Docker Volume](https://docs.docker.com/storage/volumes/). When you run the Valheim server as 
non-root user you also need to adjust the file system permission in that [Docker Volume](https://docs.docker.com/storage/volumes/) so the unprivileged 
user can access these files. This you need to do with an init container.

## Installation
I put all this together in my [valheim-dedicated-server-docker-helm](https://github.com/max-pfeiffer/valheim-dedicated-server-docker-helm)
project free for use for anyone. With this you will have your Valheim server up an running in a couple of minutes. It consists of:

* [secure Docker image for Valheim dedicated server on Docker Hub](https://hub.docker.com/r/pfeiffermax/valheim-dedicated-server)
* [Docker compose file](https://github.com/max-pfeiffer/valheim-dedicated-server-docker-helm/blob/main/examples/docker-compose/compose.yaml)
* [script for automating server update](https://github.com/max-pfeiffer/valheim-dedicated-server-docker-helm/blob/main/examples/docker-compose/valheim-server-update.sh)

Prerequisites:

* [Docker Engine](https://docs.docker.com/engine/install/) or [Docker Desktop](https://docs.docker.com/desktop/) installed
* [git installed](https://git-scm.com/install/)

If you are not familiar with [git](https://git-scm.com/) and/or don't want to install it, you can download the
[docker compose file](https://github.com/max-pfeiffer/valheim-dedicated-server-docker-helm/blob/main/examples/docker-compose/compose.yaml)
manually from GitHub or just cut and paste it's contents.

For the installing and running the Valheim server you need clone the git repository and start the Valheim server using docker compose:
```shell
git clone https://github.com/max-pfeiffer/valheim-dedicated-server-docker-helm.git
cd valheim-dedicated-server-docker-helm/examples/docker-compose
docker compose up -d
```
Stop the server:
```shell
docker compose down
```
If you want to show the logs, option `-f` follows the logs:
```shell
docker compose logs -f
```
That's basically all you need to do for running your own Valheim server. If you want to change the Valheim server settings
just change/add options in the `command` section of the `valheim-server` service in the
[docker compose file](https://github.com/max-pfeiffer/valheim-dedicated-server-docker-helm/blob/main/examples/docker-compose/compose.yaml).

## Automate Server Updates
On a Linux system you can automate the server update easily with a [script](https://github.com/max-pfeiffer/valheim-dedicated-server-docker-helm/blob/main/examples/docker-compose/valheim-server-update.sh).
If there is an update for the Valheim server, a new image will be built around 01:15 at night (time is not guaranteed by GitHub).
For me it was safe to run the update job with cron at 06:00 in the morning:
```shell
0 6 * * * /srv/valheim/valheim-server-update.sh
```

## Related Articles

* [Hosting Game Servers on Bare Metal Kubernetes with Cilium as CNI]({filename}/2026-03-21_game_server_hosting_with_cilium.md)
