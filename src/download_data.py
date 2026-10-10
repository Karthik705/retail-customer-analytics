"""Download the raw Online Retail II dataset from the UCI ML Repository.

Usage:  python -m src.download_data
Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii  (CC BY 4.0)
"""
import io
import urllib.request
import zipfile

from . import config as C

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"


def main():
    target = C.RAW_DIR / "online_retail_II.xlsx"
    if target.exists():
        print(f"Already present: {target}")
        return
    C.RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {URL} ...")
    with urllib.request.urlopen(URL, timeout=120) as resp:
        payload = resp.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        xlsx = next(n for n in zf.namelist() if n.lower().endswith(".xlsx"))
        target.write_bytes(zf.read(xlsx))
    print(f"Saved {target} ({target.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
