#!/bin/sh
# Sets up the central server (every player's account, friends, the remote games list) on a fresh Ubuntu or
# Debian VM: Docker, the firewall, the central server, Caddy (HTTPS) and the updater, in /opt/shards-of-ashen-central.
# Run it as root (or with sudo), after pointing the domain's DNS at the VM (or with no domain: it offers sslip.io):
#
#   curl -fsSL https://raw.githubusercontent.com/kriscs1/shardsofashen/main/deploy/central-setup.sh | sudo sh
#   (or copy this file to the VM and run: sudo sh central-setup.sh)
#
# Running it again is safe: it keeps your .env and the accounts, and brings everything up to date.
set -e
IMAGE="${DS_IMAGE:-ghcr.io/kriscs1/shardsofashen:latest}"
DIR="${DS_DIR:-/opt/shards-of-ashen-central}"

if [ "$(id -u)" != "0" ]; then
    echo "Run this as root (sudo sh central-setup.sh)." >&2
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

# (the internet tries SSH passwords within minutes of a VM starting: a key only, a ban for those who keep trying, and
# the system's security fixes put in by themselves)
echo "== SSH: a key to come in by, never a password"
keys=""
for f in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
    if [ -s "$f" ]; then keys=1; fi
done
conf=/etc/ssh/sshd_config.d/01-shards-of-ashen.conf
if [ -z "$keys" ]; then
    echo "   (left as it was: there's no SSH key on this VM yet, and you'd be locked out. Add yours to"
    echo "   ~/.ssh/authorized_keys and run this again.)"
elif [ -d /etc/ssh/sshd_config.d ] && grep -qi "^Include /etc/ssh/sshd_config.d" /etc/ssh/sshd_config; then
    # (01-: before the cloud's own 50-cloud-init.conf, since the first setting sshd reads is the one it keeps)
    printf "%s\n" "# From the Shards of Ashen setup (delete this file to undo): keys only, root only with a key" \
        "PasswordAuthentication no" "KbdInteractiveAuthentication no" "PermitRootLogin prohibit-password" > "$conf"
    mkdir -p /run/sshd
    if sshd -t 2>/dev/null; then
        systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true
    else
        rm -f "$conf"
        echo "   (left as it was: this sshd didn't take the settings)"
    fi
else
    echo "   (left as it was: this sshd has no sshd_config.d to add to)"
fi

if command -v apt-get >/dev/null 2>&1; then
    echo "== fail2ban (an address that keeps failing at SSH is shut out for a while) and automatic security updates"
    export DEBIAN_FRONTEND=noninteractive
    if apt-get update -qq >/dev/null && apt-get install -y -qq fail2ban python3-systemd unattended-upgrades >/dev/null
    then
        # (from the journal: Debian 12 keeps no auth.log for fail2ban to read)
        printf "%s\n" "[sshd]" "enabled = true" "backend = systemd" "maxretry = 5" "bantime = 1h" \
            > /etc/fail2ban/jail.d/shards-of-ashen.local
        systemctl enable fail2ban >/dev/null 2>&1 || true
        systemctl restart fail2ban || true
        printf "%s\n" 'APT::Periodic::Update-Package-Lists "1";' 'APT::Periodic::Unattended-Upgrade "1";' \
            > /etc/apt/apt.conf.d/20auto-upgrades
    else
        echo "   (couldn't install them just now: run this again later; the rest goes on being set up)"
    fi
fi

# (a little swap on a small VM: updates pull a new image beside the old one)
if [ ! -f /swapfile ] && [ "$(awk '/MemTotal/ {print $2}' /proc/meminfo)" -lt 2500000 ]; then
    echo "== A 1 GB swap file"
    fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

echo "== The central server's files in $DIR"
mkdir -p "$DIR"
cd "$DIR"
docker pull "$IMAGE"
docker run --rm --entrypoint cat "$IMAGE" central-deploy/docker-compose.yml > docker-compose.yml
docker run --rm --entrypoint cat "$IMAGE" central-deploy/Caddyfile > Caddyfile
if [ ! -f .env ]; then
    docker run --rm --entrypoint cat "$IMAGE" central-deploy/central.env.example > .env
    if [ -t 0 ] || [ -e /dev/tty ]; then
        default=$(grep "^DS_CENTRAL_DOMAIN=" .env | cut -d= -f2)
        printf "Its domain (its DNS must point here already) [%s, or - for none]: " "$default" > /dev/tty
        read -r domain < /dev/tty
        domain=${domain:-$default}
        if [ "$domain" = "-" ]; then
            # (no domain: the VM's own address as a name, 1-2-3-4.sslip.io, which Let's Encrypt will still sign)
            ip=$(curl -4 -fsS https://api.ipify.org || curl -4 -fsS https://ifconfig.me)
            domain="$(echo "$ip" | tr . -).sslip.io"
        fi
        printf "Your Hallisium account's name (it may use /admin; signed up with the code in the log if it's new): " > /dev/tty
        read -r admin < /dev/tty
        sed -i "s|^DS_CENTRAL_DOMAIN=.*|DS_CENTRAL_DOMAIN=$domain|; s|^DS_CENTRAL_ADMINS=.*|DS_CENTRAL_ADMINS=$admin|" .env
    fi
fi

echo "== Starting"
docker compose up -d
domain=$(grep "^DS_CENTRAL_DOMAIN=" .env | cut -d= -f2)
echo
echo "Done. In a minute or two (while Caddy gets its certificate) it's at https://$domain"
echo "Point the apps at it (web/home/config.js DS_CENTRAL_DEFAULT) and game servers (DS_CENTRAL=https://$domain)."
echo "Settings: $DIR/.env (then: cd $DIR && docker compose up -d)."
echo "Logs (the admin code is in them): cd $DIR && docker compose logs -f central"
