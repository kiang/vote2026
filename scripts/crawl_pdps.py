#!/usr/bin/env python3
"""
Crawl all PDF files from the CEC candidate asset declaration system.
https://pdps-dec.cec.gov.tw/release/formal/HomePage.html

Output structure:
  pdps/
  ├── 直轄市長/臺北市/蔣萬安.pdf
  ├── 縣（市）長/基隆市/謝國樑.pdf
  ├── 直轄市議員/臺北市/第1選舉區/汪志冰.pdf
  └── 縣（市）議員/基隆市/第1選舉區/王醒之.pdf
"""

import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://pdps-dec.cec.gov.tw/release/formal/"
SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdps")
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; vote2026-crawler/1.0)"
})


def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', '_', name.strip())


def fetch_page(url):
    resp = SESSION.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return BeautifulSoup(resp.text, "lxml")


def extract_links(soup, base_url, pattern):
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.match(pattern, href):
            full_url = urljoin(base_url, href)
            links.append((a.get_text(strip=True), full_url))
    return links


def extract_pdf_links(soup, base_url):
    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            full_url = urljoin(base_url, href)
            name = a.get_text(strip=True)
            pdfs.append((name, full_url))
    return pdfs


def download_pdf(url, save_path):
    if os.path.exists(save_path):
        return False
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    resp = SESSION.get(url, timeout=60)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(resp.content)
    return True


def download_pdfs_from_page(page_url, folder_path):
    soup = fetch_page(page_url)
    pdfs = extract_pdf_links(soup, page_url)
    for candidate_name, pdf_url in pdfs:
        filename = sanitize(candidate_name) + ".pdf"
        save_path = os.path.join(folder_path, filename)
        try:
            downloaded = download_pdf(pdf_url, save_path)
            status = "downloaded" if downloaded else "exists"
            rel = os.path.relpath(save_path, SAVE_DIR)
            print(f"  [{status}] {rel}")
        except Exception as e:
            print(f"  [error] {candidate_name} -> {pdf_url}: {e}", file=sys.stderr)
        time.sleep(0.3)
    return len(pdfs)


def crawl_mayor_pages(category_url, page_prefix, category_name):
    """Crawl Page5 (直轄市長) or Page6 (縣市長) - PDFs are at city level."""
    print(f"\n{'='*60}")
    print(f"Crawling {category_name}")
    print(f"{'='*60}")

    soup = fetch_page(category_url)
    city_pattern = rf"^{page_prefix}_\d+\.html$"
    cities = extract_links(soup, category_url, city_pattern)
    total = 0

    for city_name, city_url in cities:
        print(f"\n  {city_name}")
        folder = os.path.join(SAVE_DIR, sanitize(category_name), sanitize(city_name))
        count = download_pdfs_from_page(city_url, folder)
        total += count
        time.sleep(0.5)

    print(f"\n  Total PDFs for {category_name}: {total}")
    return total


def crawl_council_pages(category_url, page_prefix, category_name):
    """Crawl Page7 (直轄市議員) or Page8 (縣市議員) - PDFs are at district level."""
    print(f"\n{'='*60}")
    print(f"Crawling {category_name}")
    print(f"{'='*60}")

    soup = fetch_page(category_url)
    city_pattern = rf"^{page_prefix}_\d+\.html$"
    cities = extract_links(soup, category_url, city_pattern)
    total = 0

    for city_name, city_url in cities:
        print(f"\n  {city_name}")
        city_soup = fetch_page(city_url)
        city_base = os.path.basename(city_url).replace(".html", "")

        district_pattern = rf"^{city_base}_\d+\.html$"
        districts = extract_links(city_soup, city_url, district_pattern)

        if districts:
            for dist_name, dist_url in districts:
                print(f"    {dist_name}")
                folder = os.path.join(SAVE_DIR, sanitize(category_name), sanitize(city_name), sanitize(dist_name))
                count = download_pdfs_from_page(dist_url, folder)
                total += count
                time.sleep(0.5)
        else:
            folder = os.path.join(SAVE_DIR, sanitize(category_name), sanitize(city_name))
            count = download_pdfs_from_page(city_url, folder)
            total += count

        time.sleep(0.5)

    print(f"\n  Total PDFs for {category_name}: {total}")
    return total


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    print(f"Saving PDFs to: {SAVE_DIR}")

    grand_total = 0
    grand_total += crawl_mayor_pages(BASE_URL + "Page5.html", "Page5", "直轄市長")
    grand_total += crawl_mayor_pages(BASE_URL + "Page6.html", "Page6", "縣（市）長")
    grand_total += crawl_council_pages(BASE_URL + "Page7.html", "Page7", "直轄市議員")
    grand_total += crawl_council_pages(BASE_URL + "Page8.html", "Page8", "縣（市）議員")

    print(f"\n{'='*60}")
    print(f"Done! Total PDFs: {grand_total}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
