# Shards of Ashen server. Build from the game folder:  docker build -f deploy/Dockerfile -t shards-of-ashen .
# Stage 1 makes web/assets (pictures, animations, music) from the game's folders; stage 2 is the server alone.
FROM python:3.11-slim AS assets
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pygame numpy
WORKDIR /game
COPY data data
COPY maps maps
COPY sprites sprites
COPY sounds sounds
COPY ashen ashen
COPY dsengine dsengine
COPY tools tools
RUN mkdir -p web && python tools/export_web_assets.py

FROM python:3.11-slim
RUN pip install --no-cache-dir "aiohttp>=3.9" && useradd --create-home --uid 1000 dragon
WORKDIR /game
# The version on the login screen: VERSION's number, and the build (the commit count), its commit and date, given by
# whoever builds the image (GitHub's build, Test Locally.bat)
ARG DS_BUILD=
ARG DS_COMMIT=
ARG DS_BUILD_DATE=
ENV DS_BUILD=$DS_BUILD DS_COMMIT=$DS_COMMIT DS_BUILD_DATE=$DS_BUILD_DATE
COPY VERSION VERSION
COPY data data
COPY maps maps
COPY sprites sprites
COPY saves/TEMPLATE.ini saves/TEMPLATE.ini
COPY ashen ashen
COPY dsengine dsengine
COPY server server
COPY tools tools
COPY web web
# (the server's compose file travels with the game, so a server can be set up from the image alone:
#  docker run --rm ghcr.io/<you>/shardsofashen cat docker-compose.yml > docker-compose.yml && docker compose up -d)
COPY deploy/docker-compose.server.yml docker-compose.yml
# (and a public cloud server's: deploy/cloud-setup.sh takes these out of the image)
COPY deploy/docker-compose.cloud.yml cloud/docker-compose.yml
COPY deploy/Caddyfile cloud/Caddyfile
COPY deploy/cloud.env.example cloud/cloud.env.example
COPY deploy/cloud-setup.sh cloud/cloud-setup.sh
# (and Unraid's template: docker run --rm ghcr.io/<you>/shardsofashen cat unraid.xml > .../templates-user/my-ShardsOfAshen.xml)
COPY deploy/unraid/shards-of-ashen.xml unraid.xml
COPY --from=assets /game/web/assets web/assets
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh && mkdir -p /data && chown -R dragon:dragon /data /game/data
# It starts as root only to hand /data to PUID:PGID (entrypoint.sh), then runs as them (default 1000, the dragon user)
ENV DS_DB=/data/ashen.db DS_PORT=8484 DS_MAX_PLAYERS=5 PUID=1000 PGID=1000
EXPOSE 8484
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8484/health')"
STOPSIGNAL SIGTERM
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "server"]
