"""Each day's backup sent off the machine as well (the owner's wish), so a dead disk, or someone getting into the
machine, doesn't take the copies along with the database. Either or both, set in the environment:

  DS_BACKUP_COPY       a folder to copy it to: another disk, or a share on another machine (the last 14 kept there);
                       in Docker, any folder mapped to /backup-copy is it without saying so
  DS_BACKUP_S3         a bucket at any S3-style store, as https://<endpoint>/<bucket>[/<folder>] (Backblaze B2,
                       Cloudflare R2, Amazon S3, Wasabi, MinIO...), with DS_BACKUP_S3_KEY and DS_BACKUP_S3_SECRET,
                       and DS_BACKUP_S3_REGION when the endpoint's name doesn't say it (else us-east-1)
  DS_BACKUP_SUBFOLDER  a folder of its own within either, for several servers sharing one (world1, world2...)

The bucket gets it gzipped (<name>.db.gz) and is never asked to delete anything: give it a key that can write but not
delete, and a lifecycle rule that clears out old copies, so whoever got into the machine can't empty it either. It's
sent once a UTC day (a restart doesn't send another), from a thread of its own so the game never waits on it, and a
failure is logged and tried again a few times. Standard library only (it runs on a phone): S3's signature (AWS
Signature Version 4) is made here."""
import datetime
import gzip
import hashlib
import hmac
import logging
import os
import re
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("offsite")

KEEP = 14                       # (copies kept in DS_BACKUP_COPY; the bucket's own lifecycle rule clears its old ones)
TRIES = 3
WAIT = 120                      # (seconds between tries)
MARK = ".offsite"               # (in the backups folder: the UTC day a copy last went off)
MOUNTED = "/backup-copy"        # (DS_BACKUP_COPY by itself, when a folder's mapped there: Docker, Unraid's template)


def settings(env=None):
    """Where the backups go off to (a dict), or None for nowhere."""
    env = os.environ if env is None else env
    copy = env.get("DS_BACKUP_COPY", "").strip()
    if not copy and env is os.environ and os.path.ismount(MOUNTED):
        copy = MOUNTED
    s = {"copy": copy,"s3": env.get("DS_BACKUP_S3", "").strip().rstrip("/"),
         "key": env.get("DS_BACKUP_S3_KEY", "").strip(), "secret": env.get("DS_BACKUP_S3_SECRET", "").strip(),
         "region": env.get("DS_BACKUP_S3_REGION", "").strip(),
         "sub": env.get("DS_BACKUP_SUBFOLDER", "").strip().strip("/\\")}
    if s["s3"] and not (s["key"] and s["secret"]):
        log.warning("DS_BACKUP_S3 is set without DS_BACKUP_S3_KEY and DS_BACKUP_S3_SECRET: nothing goes there")
        s["s3"] = ""
    return s if s["copy"] or s["s3"] else None


def send_off(path, keep=KEEP, env=None, wait=WAIT):
    """Sends the backup at path off the machine, from a thread of its own (returned; None with nothing to do, or
    when one went off already today)."""
    s = settings(env)
    if not s:
        return None
    day = time.strftime("%Y%m%d", time.gmtime())
    mark = os.path.join(os.path.dirname(os.path.abspath(path)), MARK)
    try:
        with open(mark, encoding="ascii") as f:
            if f.read().strip() == day:
                return None
    except OSError:
        pass
    t = threading.Thread(target=_send, args=(path, keep, s, mark, day, wait), name="offsite", daemon=True)
    t.start()
    return t


def _send(path, keep, s, mark, day, wait):
    todo = [w for w in ("copy", "s3") if s[w]]
    for attempt in range(1, TRIES + 1):
        for w in list(todo):
            try:
                where = copy_to(path, os.path.join(s["copy"], s["sub"]), keep) if w == "copy" else put_s3(path, s)
                log.info("Backup sent off: %s", where)
                todo.remove(w)
            except Exception as e:
                log.warning("Sending the backup off (%s) failed, try %d of %d: %s", w, attempt, TRIES, e)
        if not todo:
            try:
                with open(mark, "w", encoding="ascii") as f:
                    f.write(day)
            except OSError:
                pass
            return
        if attempt < TRIES:
            time.sleep(wait)
    log.error("The backup wasn't sent off (%s): the next is tomorrow's", ", ".join(todo))


def copy_to(path, folder, keep=KEEP):
    """A copy of the backup in folder (written whole, then named), keeping the newest keep of its kind there."""
    os.makedirs(folder, exist_ok=True)
    name = os.path.basename(path)
    out = os.path.join(folder, name)
    shutil.copyfile(path, out + ".part")
    os.replace(out + ".part", out)
    lead = name.split("-")[0] + "-"             # (ashen-, central-: a server's own, should several share it)
    for f in sorted(f for f in os.listdir(folder) if f.startswith(lead) and f.endswith(".db"))[:-keep]:
        try:
            os.remove(os.path.join(folder, f))
        except OSError:
            pass
    return out


def put_s3(path, s, now=None):
    """The backup, gzipped, put in the bucket (its address returned)."""
    u = urllib.parse.urlsplit(s["s3"])
    if u.scheme not in ("https", "http") or not u.hostname:
        raise ValueError("DS_BACKUP_S3 isn't an https:// address")
    with open(path, "rb") as f:
        body = gzip.compress(f.read())
    parts = [p for p in u.path.split("/") if p] + ([s["sub"]] if s["sub"] else []) + [os.path.basename(path) + ".gz"]
    where = "/" + "/".join(urllib.parse.quote(p, safe="-_.~") for p in parts)
    headers = {"Content-Type": "application/gzip", "Content-Length": str(len(body))}
    headers.update(sign("PUT", u.netloc, where, headers, hashlib.sha256(body).hexdigest(), s["key"], s["secret"],
                        s["region"] or region_of(u.hostname), now))
    url = "%s://%s%s" % (u.scheme, u.netloc, where)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body, method="PUT", headers=headers),
                                    timeout=300) as r:
            r.read()
    except urllib.error.HTTPError as e:         # (the store's own reason: AccessDenied, NoSuchBucket...)
        said = re.search(r"<Code>([^<]+)</Code>", e.read(2000).decode("utf-8", "replace"))
        raise RuntimeError("%s %s" % (e.code, said.group(1) if said else e.reason)) from None
    return url


def region_of(host):
    """The region an endpoint's name gives (s3.us-west-004.backblazeb2.com, s3.eu-west-2.amazonaws.com), else
    us-east-1 (which Cloudflare R2 and MinIO take too)."""
    m = re.search(r"(?:^|[.-])s3[.-]([a-z]{2}-[a-z]+-\d+)\.", host or "")
    return m.group(1) if m else "us-east-1"


def sign(method, host, path, headers, payload_hash, key, secret, region, now=None, query="", service="s3"):
    """The headers that sign a request (AWS Signature Version 4): every header given is signed, with host. path is
    already escaped."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    amz = now.strftime("%Y%m%dT%H%M%SZ")
    h = {k.lower(): " ".join(str(v).split()) for k, v in headers.items()}
    h.update({"host": host, "x-amz-content-sha256": payload_hash, "x-amz-date": amz})
    names = sorted(h)
    signed = ";".join(names)
    canonical = "\n".join([method, path, query, "".join("%s:%s\n" % (n, h[n]) for n in names), signed, payload_hash])
    scope = "%s/%s/%s/aws4_request" % (amz[:8], region, service)
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = ("AWS4" + secret).encode()
    for part in (amz[:8], region, service, "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    return {"x-amz-date": amz, "x-amz-content-sha256": payload_hash,
            "Authorization": "AWS4-HMAC-SHA256 Credential=%s/%s,SignedHeaders=%s,Signature=%s"
                             % (key, scope, signed, sig)}
