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
COPY --from=assets /game/web/assets web/assets
RUN mkdir -p /data && chown -R dragon:dragon /data /game/Data
USER dragon
ENV DS_DB=/data/dragonsword.db DS_PORT=8080 DS_MAX_PLAYERS=5
EXPOSE 8080
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"
STOPSIGNAL SIGTERM
CMD ["python", "-m", "server"]
