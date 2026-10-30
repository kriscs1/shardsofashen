#!/bin/sh
# Sets up a public Shards of Ashen server on a fresh Ubuntu or Debian cloud VM: Docker, the firewall, the game, Caddy
# (HTTPS) and the updater, in /opt/shards-of-ashen. Run it as root (or with sudo) after pointing your domain's DNS at
# the VM:
#
#   curl -fsSL https://raw.githubusercontent.com/kriscs1/shardsofashen/main/deploy/cloud-setup.sh | sudo sh
#   (or copy this file to the VM and run: sudo sh cloud-setup.sh)
#
# Running it again is safe: it keeps your .env and the game's data, and brings everything up to date.
set -e
IMAGE="${DS_IMAGE:-ghcr.io/kriscs1/shardsofashen:latest}"
DIR="${DS_DIR:-/opt/shards-of-ashen}"

if [ "$(id -u)" != "0" ]; then
    echo "Run this as root (sudo sh cloud-setup.sh)." >&2
    exit 1
fi

echo "== Docker"
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker >/dev/null 2>&1 || true

echo "== The firewall (SSH, HTTP and HTTPS only)"
if command -v ufw >/dev/null 2>&1; then
    ufw allow OpenSSH >/dev/null
    ufw allow 80/tcp >/dev/null
    ufw allow 443 >/dev/null
    ufw --force enable >/dev/null
fi

# (a little swap on a small VM: the game's memory is steady, but updates pull a new image beside the old one)
if [ ! -f /swapfile ] && [ "$(awk '/MemTotal/ {print $2}' /proc/meminfo)" -lt 2500000 ]; then
    echo "== A 1 GB swap file"
    fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

echo "== The game's files in $DIR"
mkdir -p "$DIR"
cd "$DIR"
docker pull "$IMAGE"
docker run --rm --entrypoint cat "$IMAGE" cloud/docker-compose.yml > docker-compose.yml
docker run --rm --entrypoint cat "$IMAGE" cloud/Caddyfile > Caddyfile
if [ ! -f .env ]; then
    docker run --rm --entrypoint cat "$IMAGE" cloud/cloud.env.example > .env
    if [ -t 0 ] || [ -e /dev/tty ]; then
        printf "Your server's domain (its DNS must point here already): " > /dev/tty
        read -r domain < /dev/tty
        printf "Your admin character's name (you'll make it first): " > /dev/tty
        read -r admin < /dev/tty
        sed -i "s|^DS_DOMAIN=.*|DS_DOMAIN=$domain|; s|^DS_ADMINS=.*|DS_ADMINS=$admin|" .env
    fi
fi
if grep -q "^DS_DOMAIN=play.example.com" .env; then
    echo "Set DS_DOMAIN in $DIR/.env, then run: cd $DIR && docker compose up -d" >&2
    exit 1
fi

echo "== Starting"
docker compose up -d
domain=$(grep "^DS_DOMAIN=" .env | cut -d= -f2)
echo
echo "Done. In a minute or two (while Caddy gets its certificate) the game is at https://$domain"
echo "Make your admin character there first. Settings: $DIR/.env (then: cd $DIR && docker compose up -d)."
echo "Logs: cd $DIR && docker compose logs -f game        Accounts: docker compose exec game python tools/admin.py list"
