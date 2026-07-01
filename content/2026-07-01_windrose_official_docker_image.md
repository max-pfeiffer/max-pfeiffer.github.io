Title: Kraken Express published an official Windrose Dedicated Server Image 
Description: In depth technical analysis of the official Windrose Server Image   
Summary: In depth technical analysis of the official Windrose Server Image
Date: 2026-07-01 23:00
Author: Max Pfeiffer
Lang: en
Keywords: Windrose, Dedicated Server, Docker, Docker Compose
Image: https://max-pfeiffer.github.io/images/2026-07-01_windrose_official_docker_image.png

Kraken Express published their [official Windrose Docker image on Docker Hub](https://hub.docker.com/r/windroseserver/windroseserver)
in May. Also, they updated their [dedicated server guide with some instructions](https://playwindrose.com/dedicated-server-guide/#wsg-docker).
There seems to be no automation in place and the image is already outdated today (1.7.2026) as they just published a major
content update. This makes the image basically useless because clients are updated by Steam automatically.
Hey Kraken Express, can I help as professional DevOps engineer?

![2026-07-01_windrose_official_docker_image.png]({static}/images/2026-07-01_windrose_official_docker_image.png)

## Analysis Overview
It's a thin Ubuntu 22.04 wrapper around a stock Unreal Engine 5 Linux dedicated-server build (project codename R5,
~330 MB stripped x86-64 binary, amd64 only). There's no entrypoint logic, no env-var handling, no supervisor.
The container just runs UE's standard launcher script as user ue_user, and all configuration happens through JSON files
that you're expected to bind-mount.

## Reconstructed Dockerfile
From the buildkit layer history, the Dockerfile is essentially:

```Dockerfile
FROM ubuntu:22.04
EXPOSE 7777/tcp 7777/udp
ARG SERVER_FILES=server_files
RUN apt-get update && apt-get install -y ca-certificates && update-ca-certificates
RUN apt-get update && apt-get install -y libcurl4
RUN useradd --create-home --home /home/ue_user --shell /bin/bash --uid 1000 ue_user
RUN adduser ue_user sudo
RUN mkdir -p /home/ue_user/app/R5/Saved && chown -R ue_user:ue_user /home/ue_user/app/R5/Saved
USER ue_user
COPY server_files /home/ue_user/app        # 5.17 GB game payload
WORKDIR /home/ue_user/app/
RUN chmod a+x ./WindroseServer.sh ./R5/Plugins/3rdParty/Sentry/Binaries/Linux/crashpad_handler
VOLUME /home/ue_user/app/R5/Saved
CMD ["/bin/bash", "-c", "./WindroseServer.sh || sleep 15"]
```

## The launch chain
CMD runs ./WindroseServer.sh || sleep 15. The || sleep 15 just keeps the container alive 15 seconds after a crash — 
presumably to soften restart-loop hammering and give you a window to grab logs. WindroseServer.sh is the
standard UE-generated launcher, nothing more:

```shell
UE_PROJECT_ROOT=$(dirname "$(echo "$0" | xargs readlink -f)")
chmod +x "$UE_PROJECT_ROOT/R5/Binaries/Linux/WindroseServer-Linux-Shipping"
"$UE_PROJECT_ROOT/R5/Binaries/Linux/WindroseServer-Linux-Shipping" R5 "$@"
```
So the actual process is WindroseServer-Linux-Shipping R5, running in the foreground as PID under bash, as uid 1000.
No arguments are passed by default (the CMD forwards nothing), though you could append UE flags like -log by
overriding the command.

## Configuration model — files, not env vars
The binary takes no environment variables. Everything comes from two JSON files (I confirmed via strings that the
binary parses PersistentServerId, InviteCode, WorldIslandId,
MaxPlayerCount, UseDirectConnection, etc. as JSON keys — there's even a "PersistentServerId is empty" error string):

* /home/ue_user/app/R5/ServerDescription.json — server identity and networking. The image ships it as an empty 0-byte file,
  deliberately, so it exists as a bind-mount target. On first start the server generates it with a random
  PersistentServerId, InviteCode, and WorldIslandId. It may only be edited while the server is stopped, and the server
  can rewrite any field at runtime.
* WorldDescription.json — one per world, generated under R5/Saved/SaveProfiles/Default/RocksDB_v2/<version>/Worlds/<id>/,
  holds difficulty preset and world settings. ServerDescription.json's WorldIslandId must match a world's IslandId.

Saves are a RocksDB database under R5/Saved/SaveProfiles/Default/, with zip'd autosave backups in RocksDB_v2_Backups/
marked _Latest (a missing _Latest is treated as a critical error; AutoLoadLatestBackupIfHasBroken controls
auto-recovery).

The image bundles its own docs (DedicatedServer.md, SaveWorkflow.md) which prescribe exactly this Docker usage:
```shell
docker run --user ue_user -p 7777:7777/tcp -p 7777:7777/udp \
 -v <saves>/Saved:/home/ue_user/app/R5/Saved \
 -v <saves>/ServerDescription.json:/home/ue_user/app/R5/ServerDescription.json \
 windroseserver/windroseserver:latest
```

With "UseDirectConnection": true and "DirectConnectionServerPort": 7777 required for the port mapping to be meaningful.
Otherwise, the server uses ICE/P2P via a "Connection Service" (regions EU/SEA/CIS) and the invite-code
flow, and port 7777 is irrelevant.

## Notable payload details
Bundled third-party bits: Sentry crashpad_handler (crash reporting), Steamworks 1.57, MsQuic 2.20, ONNX Runtime 1.20
(NNE plugin), and a set of Boost 1.85 libs including libboost_python311. There's also mention of a
R5WorldDescriptionUpdater.exe tool in the docs for re-validating hand-edited world files — but only the Windows .exe is
referenced; no Linux equivalent ships in the image.

Config must be injected as files (an initContainer or templated mount writing ServerDescription.json is the right shape), 
and note the bind-mount subtlety that flow, and port 7777 is irrelevant.

## Conclusion
It seems to be an early stage build with quite a way still to go. At least the dedicated Windrose Server runs natively
on Linux now. The absence of configuration options via environment variables makes it a no-go for Kubernetes as 
hosting platform. But it's an image I could build ontop. The fact that the latest image version is outdated compared
to the client versions distributed via Steam makes it useless eventually.

## Related Articles

* [A guide for setting up a Windrose dedicated server using Docker and Docker Compose]({filename}/2026-04-28_windrose_dedicated_server_with_docker.md)
