import requests
import re
import json
import subprocess
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (RedTeam-OSINT/1.0)"
}

EMAIL_REGEX = r"\b[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]{1,253}\.[a-zA-Z]{2,}\b"

PHONE_REGEX = r"""
\b
(?:\+?\d{1,3}[\s.-]?)?
(?:\(?\d{3}\)?[\s.-]?)
\d{3}[\s.-]?\d{4}
\b
"""

def normalize(v, t, s, c=0.6):
    return {
        "value": v,
        "type": t,
        "source": s,
        "confidence": c
    }

def scrape_website(d):
    print(f"[+] Scraping website: https://{d}")
    a = []
    try:
        r = requests.get(f"https://{d}", headers=HEADERS, timeout=10)
        x = r.text

        for e in set(re.findall(EMAIL_REGEX, x)):
            a.append(normalize(e, "email", "website", 0.9))

        for p in set(re.findall(PHONE_REGEX, x, re.VERBOSE)):
            a.append(normalize(p.strip(), "phone", "website", 0.7))

        s = BeautifulSoup(x, "lxml")
        for l in s.find_all("a", href=True):
            h = l["href"]
            if h.startswith("mailto:"):
                a.append(normalize(h.replace("mailto:", ""), "email", "website", 0.95))
            if h.startswith("tel:"):
                a.append(normalize(h.replace("tel:", ""), "phone", "website", 0.85))

    except Exception as e:
        print(f"[!] Website error: {e}")

    return a

def scrape_pdfs(d):
    print("[+] Discovering PDFs")
    a = []
    try:
        r = requests.get(f"https://{d}", headers=HEADERS, timeout=10)
        s = BeautifulSoup(r.text, "lxml")

        for l in s.find_all("a", href=True):
            h = l["href"]
            if h.lower().endswith(".pdf"):
                if not h.startswith("http"):
                    h = f"https://{d}/{h.lstrip('/')}"
                a.append(normalize(h, "pdf", "website", 0.6))
    except:
        pass
    return a

def scrape_crtsh(d):
    print("[+] Querying crt.sh")
    a = []
    try:
        u = f"https://crt.sh/?q=%25.{d}&output=json"
        r = requests.get(u, timeout=15)

        for c in r.json():
            n = c.get("name_value", "")
            for e in re.findall(EMAIL_REGEX, n):
                a.append(normalize(e, "email", "crt.sh", 0.75))
    except:
        pass
    return a

def scrape_reddit(q):
    print(f"[+] Scraping Reddit: {q}")
    a = []
    try:
        u = f"https://www.reddit.com/search.json?q={q}"
        r = requests.get(u, headers=HEADERS, timeout=10)
        d = r.json()

        for p in d.get("data", {}).get("children", []):
            t = p["data"].get("title", "")
            for e in re.findall(EMAIL_REGEX, t):
                a.append(normalize(e, "email", "reddit", 0.5))
    except:
        pass
    return a

def scrape_nitter(u):
    print(f"[+] Scraping Nitter: {u}")
    a = []
    try:
        r = requests.get(f"https://nitter.net/{u}", headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return a

        s = BeautifulSoup(r.text, "lxml")
        t = s.find_all("div", class_="tweet-content")

        for x in t[:5]:
            for e in re.findall(EMAIL_REGEX, x.text):
                a.append(normalize(e, "email", "twitter", 0.6))
            for p in re.findall(PHONE_REGEX, x.text, re.VERBOSE):
                a.append(normalize(p.strip(), "phone", "twitter", 0.6))
    except:
        pass
    return a

def run_theharvester(d):
    print("[+] Running theHarvester")
    try:
        subprocess.run(
            ["theHarvester", "-d", d, "-b", "duckduckgo,crtsh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )
    except:
        pass
    return []

if __name__ == "__main__":
    d = input("Enter domain: ").strip()
    t = input("Enter twitter handle: ").strip()

    r = []
    r += scrape_website(d)
    r += scrape_pdfs(d)
    r += scrape_crtsh(d)
    r += scrape_reddit(d)
    r += scrape_nitter(t)
    r += run_theharvester(d)

    u = {json.dumps(i, sort_keys=True): i for i in r}
    r = list(u.values())

    with open("recon_output.json", "w") as f:
        json.dump(r, f, indent=4)

    print(f"\n[✔] Recon complete — {len(r)} valid artifacts saved")
