#!/usr/bin/env python3
"""WedFace face-scan robot — GitHub Actions par chalta hai.

Kya karta hai (har run me):
  1. Pending guest selfies ke embeddings banata hai (sabse pehle — guest wait kar raha hota hai)
  2. Har LIVE wedding ke har folder ke NAYE photos scan karke faces save karta hai

Models: SCRFD detection + ArcFace 512-dim embedding (InsightFace buffalo_s).
Embeddings L2-normalised, little-endian float32, base64 — server par model_v=2.

Privacy: logs me sirf wedding/folder ke NUMBER chhapte hain — naam, code,
ya photo URL kabhi nahi (public repo ke logs sab dekh sakte hain).
"""
import os
import sys
import time
import json
import base64

import numpy as np
import requests
import cv2
from insightface.app import FaceAnalysis

# GitHub runners par IPv6 nahi hota. Domain ke AAAA records hone se robot IPv6
# try karta tha -> "[Errno 101] Network is unreachable". Isliye sirf IPv4 use karo.
import socket as _sock
_orig_gai = _sock.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_gai(host, port, _sock.AF_INET, type, proto, flags)
_sock.getaddrinfo = _ipv4_only

BASE = os.environ.get('WF_BASE', 'https://wedface.in').rstrip('/')
TOKEN = os.environ.get('WF_TOKEN', '')
DEADLINE = time.time() + 45 * 60          # runner limit se pehle khud ruk jao
MODEL_V = 2
DET_SIZE = (768, 768)                     # bada = group photos ke chhote faces bhi milte hain
MIN_FACE = 40                             # px — isse chhote face ka embedding weak hota hai
MIN_SCORE = 0.5
BATCH = 10                                # har 10 photos par server ko checkpoint

if not TOKEN:
    print('WF_TOKEN secret set nahi hai', file=sys.stderr)
    sys.exit(1)

sess = requests.Session()
app = None


def api(path):
    return BASE + '/api/' + path + ('&' if '?' in path else '?') + 't=' + requests.utils.quote(TOKEN)


def jget(url):
    r = sess.get(url, timeout=90)
    if not r.ok:
        raise RuntimeError('GET %s -> %d' % (url.split('?')[0], r.status_code))
    return r.json()


def jpost(url, fields):
    r = sess.post(url, data=fields, timeout=90)
    if not r.ok:
        raise RuntimeError('POST %s -> %d' % (url.split('?')[0], r.status_code))
    return r.json()


def load_models():
    global app
    if app is not None:
        return
    a = FaceAnalysis(name='buffalo_s',
                     allowed_modules=['detection', 'recognition'],
                     providers=['CPUExecutionProvider'])
    a.prepare(ctx_id=-1, det_size=DET_SIZE)
    app = a
    print('models ready (buffalo_s / ArcFace 512-dim)')


def b64emb(emb):
    return base64.b64encode(np.asarray(emb, dtype='<f4').tobytes()).decode('ascii')


def detect(img_bytes):
    """image bytes → list of base64 embeddings (ek per face)"""
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)   # BGR — insightface yahi chahta hai
    if img is None:
        return []
    out = []
    for f in app.get(img):
        x1, y1, x2, y2 = f.bbox
        if min(x2 - x1, y2 - y1) < MIN_FACE:
            continue
        if float(getattr(f, 'det_score', 1.0)) < MIN_SCORE:
            continue
        emb = getattr(f, 'normed_embedding', None)
        if emb is None:
            continue
        out.append(b64emb(emb))
    return out


def process_enrollments():
    """Guest selfies — albums se pehle, taaki guest ko photos jaldi milein."""
    try:
        jobs = (jget(api('enroll.php')) or {}).get('jobs') or []
    except Exception as e:
        print('enroll: list nahi mili (%s)' % e)
        return
    if not jobs:
        return
    print('%d selfie(s) pending' % len(jobs))
    load_models()
    for j in jobs:
        if time.time() > DEADLINE:
            return
        gid = j.get('g')
        k = j.get('k', '')
        try:
            r = sess.get(j.get('img', ''), timeout=60)
            if not r.ok:
                raise RuntimeError('img %d' % r.status_code)
            arr = np.frombuffer(r.content, dtype=np.uint8)
            im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            faces = app.get(im) if im is not None else []
            if not faces:
                jpost(api('enroll.php'), {'g': gid, 'k': k, 'fail': '1'})
                print('  guest %s: chehra clear nahi' % gid)
                continue
            # sabse bada face = selfie lene wala
            faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
            jpost(api('enroll.php'), {'g': gid, 'k': k, 'd': b64emb(faces[0].normed_embedding), 'v': MODEL_V})
            print('  guest %s: ok' % gid)
        except Exception as e:
            print('  guest %s: error (%s)' % (gid, e))


def scan_folder(wid, fl, names_by_url):
    """ek folder ke naye photos scan karke embeddings bhejo"""
    i, h, mode = fl['i'], fl['h'], fl['mode']
    q = '&w=%d&i=%d' % (wid, i)
    jpost(api('save.php'), {'action': 'start', 'w': wid, 'i': i, 'h': h, 'mode': mode})

    alb = jget(api('album.php?fresh=1' + q))
    photos = (alb or {}).get('photos') or []
    names = (alb or {}).get('names') or []
    for idx, u in enumerate(photos):
        if idx < len(names) and names[idx]:
            names_by_url[u] = names[idx]
    if not photos:
        note = (alb or {}).get('error') or 'photos nahi mili'
        jpost(api('save.php'), {'action': 'error', 'w': wid, 'i': i, 'h': h, 'note': note})
        print('  W%d F%d: album empty/error' % (wid, i))
        return {'done': 0, 'faces': 0, 'finished': False}

    fl_new = jpost(api('save.php'), {'action': 'filter', 'w': wid, 'i': i, 'urls': json.dumps(photos)})
    targets = fl_new.get('new') or []
    if not targets:
        jpost(api('save.php'), {'action': 'done', 'w': wid, 'i': i, 'h': h})
        print('  W%d F%d: up to date (%d photos)' % (wid, i, len(photos)))
        return {'done': 0, 'faces': 0, 'finished': True}

    load_models()
    print('  W%d F%d: %d naye photos' % (wid, i, len(targets)))
    faces = 0
    done = 0
    batch = []

    def flush():
        if not batch:
            return
        items = json.dumps(batch)
        del batch[:]
        jpost(api('save.php'), {'action': 'add', 'w': wid, 'i': i, 'items': items, 'v': MODEL_V})

    for u in targets:
        if time.time() > DEADLINE:
            flush()
            print('  W%d F%d: time limit — %d/%d, agli run me continue' % (wid, i, done, len(targets)))
            return {'done': done, 'faces': faces, 'finished': False}
        try:
            r = sess.get(u + '=w1200', timeout=60)
            if not r.ok:
                raise RuntimeError('img %d' % r.status_code)
            ds = detect(r.content)
            batch.append({'url': u, 'name': names_by_url.get(u, ''), 'd': ds})
            faces += len(ds)
        except Exception:
            batch.append({'url': u, 'name': names_by_url.get(u, ''), 'd': []})   # fail par bhi checkpoint
        done += 1
        if len(batch) >= BATCH:
            flush()
        if done % 50 == 0:
            print('  ... W%d F%d: %d/%d — %d faces' % (wid, i, done, len(targets), faces))
    flush()
    jpost(api('save.php'), {'action': 'done', 'w': wid, 'i': i, 'h': h})
    print('  ok W%d F%d: %d photos — %d faces' % (wid, i, done, faces))
    return {'done': done, 'faces': faces, 'finished': True}


def main():
    process_enrollments()
    j = jget(api('jobs.php'))
    jobs = (j or {}).get('jobs') or []
    print('%d live wedding(s)' % len(jobs))
    tot_p = 0
    tot_f = 0
    for job in jobs:
        if time.time() > DEADLINE:
            break
        wid = int(job['w'])
        names_by_url = {}
        for fl in (job.get('folders') or []):
            if time.time() > DEADLINE:
                break
            try:
                r = scan_folder(wid, fl, names_by_url)
                tot_p += r['done']
                tot_f += r['faces']
            except Exception as e:
                print('  W%d F%s: error (%s)' % (wid, fl.get('i'), e))
    # aakhri me phir dekho — scan ke dauraan naye selfies aaye ho sakte hain
    process_enrollments()
    print('Run complete: %d photos, %d faces.' % (tot_p, tot_f))


if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print('FATAL:', e, file=sys.stderr)
        sys.exit(1)
