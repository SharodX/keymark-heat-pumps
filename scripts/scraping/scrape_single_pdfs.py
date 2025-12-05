# scrape_keymark_subtypes_resume.py
import os, time, csv, requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE = "https://www.heatpumpkeymark.com"
LIST_URL = "https://www.heatpumpkeymark.com/en/?type=109126"
OUTDIR = "input_keymark_pdfs"
os.makedirs(OUTDIR, exist_ok=True)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36")
}
session = requests.Session()
session.headers.update(HEADERS)
SLEEP = 1
RESUME_LOG = "resume.log"   # 🔹 new


def fetch(url, retries=3, backoff=10):
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=90)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"Fetch attempt {attempt} failed for {url}: {e}")
            if attempt < retries:
                time.sleep(backoff * attempt)
            else:
                raise


def get_manufacturer_links():
    html = fetch(LIST_URL)
    soup = BeautifulSoup(html, "html.parser")
    manu_links = []
    for a in soup.select("a"):
        href = a.get("href") or ""
        if "holder" in href:
            manu_links.append(urljoin(BASE, href))
    manu_links = sorted(set(manu_links))
    print("Manufacturers found:", len(manu_links))   # 🔹 show count
    for i, link in enumerate(manu_links, 1):         # 🔹 list them
        print(f"{i:3d}: {link}")
    return manu_links


def get_subtype_rows(manufacturer_url):
    html = fetch(manufacturer_url)
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.select("table tr"):
        cols = tr.find_all("td")
        if len(cols) >= 4:
            subtype_a = cols[0].find("a")
            if subtype_a and "subtype" in (subtype_a.get("href") or ""):
                subtype_name = subtype_a.get_text(strip=True)
                subtype_url = urljoin(BASE, subtype_a["href"])
                cert_holder = cols[1].get_text(strip=True)
                hp_type = cols[2].get_text(strip=True)
                cert_body = cols[3].get_text(strip=True)
                rows.append((subtype_name, cert_holder, hp_type, cert_body, subtype_url))
    return rows


def parse_subtype_page(url):
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a"):
        href = a.get("href") or ""
        if "generatePdf" in href:
            return urljoin(BASE, href)
    return None


def safe_name(text):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)


def download_pdf(url, manu_name, subtype_name, hp_type, count):
    manu = safe_name(manu_name)[:40]
    sub  = safe_name(subtype_name)[:60]
    hpt  = safe_name(hp_type)[:40]
    fname = f"{manu}_{sub}_{hpt}_{count}.pdf"
    outpath = os.path.join(OUTDIR, fname)

    if os.path.exists(outpath) and os.path.getsize(outpath) > 0:
        print("Skipping existing:", outpath)
        return outpath, False

    try:
        r = session.get(url, timeout=90)
        r.raise_for_status()
        with open(outpath, "wb") as f:
            f.write(r.content)
        print("Downloaded:", outpath)
        return outpath, True
    except Exception as e:
        print("Failed to download:", url, e)
        return "", False


def main(start_index=0):   # 🔹 allow resume from index
    manu_links = get_manufacturer_links()

    csv_exists = os.path.exists("submodels.csv")
    with open("submodels.csv", "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not csv_exists:
            writer.writerow([
                "Manufacturer", "Subtype", "Heat Pump Type",
                "Certification Body", "PDF Path"
            ])

        for manu_idx, manu_url in enumerate(manu_links, 0):
            if manu_idx < start_index:   # 🔹 skip until start_index
                continue

            rows = get_subtype_rows(manu_url)
            if not rows:
                continue
            manu_name = rows[0][1]
            print(f"\n[{manu_idx}] --- {manu_name} ---")   # 🔹 log index + name

            # 🔹 write log file for restart
            with open(RESUME_LOG, "w", encoding="utf-8") as logf:
                logf.write(str(manu_idx))

            for s_idx, (subtype_name, cert_holder, hp_type, cert_body, st_url) in enumerate(rows, 1):
                pdf_link = parse_subtype_page(st_url)
                pdf_path = ""
                if pdf_link:
                    pdf_path, hit = download_pdf(pdf_link, manu_name, subtype_name, hp_type, s_idx)
                    if hit:
                        time.sleep(SLEEP)
                writer.writerow([
                    cert_holder,
                    subtype_name,
                    hp_type,
                    cert_body,
                    pdf_path
                ])


if __name__ == "__main__":
    # 🔹 resume from last logged manufacturer index if available
    start = 0
    if os.path.exists(RESUME_LOG):
        try:
            with open(RESUME_LOG, "r", encoding="utf-8") as f:
                start = int(f.read().strip())
            print(f"Resuming from manufacturer index {start}")
        except:
            pass

    main(start_index=start)
