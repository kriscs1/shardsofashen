# Dragon Sword server. Build from the game folder:  docker build -f deploy/Dockerfile -t dragonsword .
# Stage 1 makes web/assets (pictures, animations, music) from the game's folders; stage 2 is the server alone.
FROM python:3.11-slim AS assets
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pygame numpy
WORKDIR /game
COPY Data Data
COPY Maps Maps
COPY Sprites Sprites
COPY Sounds Sounds
COPY dragonsword dragonsword
COPY dsengine dsengine
COPY tools tools
RUN mkdir -p web && python tools/export_web_assets.py

FROM python:3.11-slim
RUN pip install --no-cache-dir "aiohttp>=3.9" && useradd --create-home --uid 1000 dragon
WORKDIR /game
COPY Data Data
COPY Maps Maps
COPY Sprites Sprites
COPY Saves/TEMPLATE.ini Saves/TEMPLATE.ini
COPY dragonsword dragonsword
COPY dsengine dsengine
COPY server server
COPY tools tools
COPY web web
# (the server's compose file travels with the game, so a server can be set up from the image alone:
#  docker run --rm ghcr.io/<you>/dragonsword cat docker-compose.yml > docker-compose.yml && docker compose up -d)
COPY deploy/server-pc/docker-compose.yml docker-compose.yml
# (and Unraid's template: docker run --rm ghcr.io/<you>/dragonsword cat unraid.xml > .../templates-user/my-DragonSword.xml)
COPY deploy/unraid/dragonsword.xml unraid.xml
COPY --from=assets /game/web/assets web/assets
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh && mkdir -p /data && chown -R dragon:dragon /data /game/Data
# It starts as root only to hand /data to PUID:PGID (entrypoint.sh), then runs as them (default 1000, the dragon user)
ENV DS_DB=/data/dragonsword.db DS_PORT=8080 DS_MAX_PLAYERS=5 PUID=1000 PGID=1000
EXPOSE 8080
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"
STOPSIGNAL SIGTERM
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "server"]
