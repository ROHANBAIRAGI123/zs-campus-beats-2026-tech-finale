"""OS-agnostic downloader for the ZS Tech Challenge bulk data.

Usage:
    python3 scripts/download_data.py            # download all tables
    python3 scripts/download_data.py orders     # download a single table
    python3 scripts/download_data.py --check    # verify checksums after download

Files are streamed to ./data/<table>.csv.gz from the public S3 bucket
configured in MANIFEST_URL below. No AWS credentials required.

Works on Linux, macOS, and Windows with Python 3.8+. Only stdlib used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ----------------------------------------------------------------------------
# CONFIGURE THIS — point at the S3 bucket where the dataset is hosted.
# The manifest is a JSON file: { "files": [ {"name":"orders.csv.gz","url":"...","sha256":"...","bytes":12345}, ... ] }
# ----------------------------------------------------------------------------
DEFAULT_MANIFEST_URL = os.environ.get(
    "ZSCHALLENGE_MANIFEST_URL",
    "https://zs-tech-challenge-2026.s3.ap-south-1.amazonaws.com/v1/manifest.json",
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

CHUNK = 1024 * 1024  # 1 MB


def fetch_manifest(url: str) -> dict:
    print(f"→ fetching manifest from {url}")
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"manifest fetch failed (HTTP {e.code}). "
                 f"Check that ZSCHALLENGE_MANIFEST_URL is correct or that you have network access.")
    except urllib.error.URLError as e:
        sys.exit(f"manifest fetch failed: {e.reason}. "
                 f"Check your network / DNS, or pass --manifest-url to override.")


def human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} GB"


def download_one(entry: dict, out_dir: Path, *, force: bool = False) -> None:
    name = entry["name"]
    url = entry["url"]
    expected_sha = entry.get("sha256")
    expected_bytes = entry.get("bytes")
    target = out_dir / name

    if target.exists() and not force:
        if expected_bytes and target.stat().st_size == expected_bytes:
            print(f"  ✓ {name} already present ({human_bytes(target.stat().st_size)}); skipping")
            return
        print(f"  ! {name} present but size mismatch — re-downloading")

    tmp = target.with_suffix(target.suffix + ".part")
    print(f"  ↓ {name} ({human_bytes(expected_bytes) if expected_bytes else '?'})")
    with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as f:
        downloaded = 0
        while True:
            buf = resp.read(CHUNK)
            if not buf:
                break
            f.write(buf)
            downloaded += len(buf)
            if expected_bytes:
                pct = downloaded * 100 // expected_bytes
                print(f"\r    {pct:3d}%  {human_bytes(downloaded)} / {human_bytes(expected_bytes)}",
                      end="", flush=True)
        print()
    tmp.rename(target)

    if expected_sha:
        actual = sha256_file(target)
        if actual != expected_sha:
            target.unlink()
            sys.exit(f"  ✗ checksum mismatch for {name}: expected {expected_sha}, got {actual}")
        print(f"    sha256 ok")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            buf = f.read(CHUNK)
            if not buf: break
            h.update(buf)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Download the ZS Tech Challenge dataset.")
    ap.add_argument("tables", nargs="*", help="optional list of table names (without .csv.gz)")
    ap.add_argument("--manifest-url", default=DEFAULT_MANIFEST_URL)
    ap.add_argument("--force", action="store_true", help="re-download even if present")
    ap.add_argument("--check", action="store_true", help="verify checksums of existing files only")
    args = ap.parse_args()

    manifest = fetch_manifest(args.manifest_url)
    files = manifest["files"]
    if args.tables:
        wanted = set(args.tables)
        files = [f for f in files if f["name"].split(".")[0] in wanted]
        if not files:
            sys.exit(f"no manifest entries match: {sorted(wanted)}")

    if args.check:
        for entry in files:
            target = DATA / entry["name"]
            if not target.exists():
                print(f"  ? {entry['name']} missing")
                continue
            actual = sha256_file(target)
            ok = "✓" if actual == entry.get("sha256") else "✗"
            print(f"  {ok} {entry['name']}  {actual}")
        return

    total = sum(f.get("bytes", 0) for f in files)
    print(f"Will download {len(files)} files, total {human_bytes(total)} into {DATA}")
    for entry in files:
        download_one(entry, DATA, force=args.force)
    print("Done.")


if __name__ == "__main__":
    main()
