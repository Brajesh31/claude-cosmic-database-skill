#!/usr/bin/env python3
"""Download a COSMIC file from an authorized HTTPS scripted-download URL.

This helper intentionally does not automate account login, collect passwords,
or bypass download permissions. Sign in through the data portal, choose a
product and release, use its Scripted Download instructions, and pass the
authorized HTTPS URL to this script.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

CHUNK_SIZE = 1024 * 1024
DEFAULT_TIMEOUT = 90

# These are path hints from common product examples. Confirm current names in
# the release-specific download catalogue before relying on them.
COMMON_PATHS = {
    "mutations": "GRCh38/cosmic/latest/CosmicMutantExport.tsv.gz",
    "mutations_vcf": "GRCh38/cosmic/latest/CosmicCodingMuts.vcf.gz",
    "gene_census": "GRCh38/cosmic/latest/cancer_gene_census.csv",
    "fusion_genes": "GRCh38/cosmic/latest/CosmicFusionExport.tsv.gz",
    "copy_number": "GRCh38/cosmic/latest/CosmicCompleteCNA.tsv.gz",
}


def get_common_file_path(data_type: str, genome_assembly: str = "GRCh38") -> str:
    """Return a documented example path for a known product family."""
    assembly = genome_assembly.upper()
    if assembly not in {"GRCH37", "GRCH38"}:
        raise ValueError("genome_assembly must be GRCh37 or GRCh38")
    try:
        path = COMMON_PATHS[data_type.lower()]
    except KeyError as exc:
        available = ", ".join(sorted(COMMON_PATHS))
        raise ValueError(f"Unsupported data_type {data_type!r}. Known types: {available}") from exc
    prefix = "GRCh37" if assembly == "GRCH37" else "GRCh38"
    return re.sub(r"^GRCh38/", f"{prefix}/", path)


def _validate_url(download_url: str) -> None:
    parsed = urlsplit(download_url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("download_url must be a valid HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("Do not embed account credentials in the download URL")
    if any(char.isspace() for char in download_url):
        raise ValueError("download_url contains whitespace")


def download_cosmic_file(
    download_url: str,
    output_filename: str | Path,
    expected_sha256: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Stream an authorized file to disk and return size and SHA-256.

    The URL may contain a short-lived access token issued by the portal. The
    URL is never printed. Do not share it or commit it to source control.
    """
    _validate_url(download_url)
    if timeout < 1:
        raise ValueError("timeout must be a positive number of seconds")

    expected = expected_sha256.lower().strip() if expected_sha256 else None
    if expected and not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("expected_sha256 must contain exactly 64 hexadecimal characters")

    destination = Path(output_filename).expanduser()
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists: {destination}. Use overwrite=True to replace it.")
    if destination.exists() and destination.is_dir():
        raise IsADirectoryError(f"Destination is a directory: {destination}")

    temp_path: Path | None = None
    digest = hashlib.sha256()
    total = 0
    first_bytes = b""
    content_type = ""

    request = Request(
        download_url,
        headers={"User-Agent": "COSMIC-data-download-helper/1.0"},
        method="GET",
    )

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.name}.",
            suffix=".part",
            dir=str(parent),
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            with urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if status < 200 or status >= 300:
                    raise RuntimeError(f"Download returned unexpected HTTP status {status}")

                content_type = response.headers.get("Content-Type", "").lower()
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    if not first_bytes:
                        first_bytes = chunk[:512]
                    temp_file.write(chunk)
                    digest.update(chunk)
                    total += len(chunk)

        if total == 0:
            raise RuntimeError("The download was empty")

        prefix = first_bytes.lstrip().lower()
        if "text/html" in content_type or prefix.startswith((b"<!doctype html", b"<html")):
            raise RuntimeError(
                "The server returned an HTML page, not a data file. "
                "The scripted URL may have expired or require a fresh authenticated session."
            )

        actual_sha256 = digest.hexdigest()
        if expected and actual_sha256 != expected:
            raise RuntimeError(
                f"SHA-256 mismatch: expected {expected}, received {actual_sha256}. "
                "The incomplete file was not installed."
            )

        if destination.exists() and not overwrite:
            raise FileExistsError(f"Destination appeared during download: {destination}")

        os.replace(temp_path, destination)
        temp_path = None

        return {
            "path": str(destination),
            "bytes": total,
            "sha256": actual_sha256,
        }

    except HTTPError as exc:
        raise RuntimeError(f"Download failed with HTTP status {exc.code}") from None
    except URLError as exc:
        reason = getattr(exc, "reason", "network error")
        raise RuntimeError(f"Download failed: {reason}") from None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download a COSMIC file from an authorized HTTPS scripted-download URL."
    )
    parser.add_argument("--url", required=True, help="Authorized HTTPS URL from the portal's scripted-download instructions")
    parser.add_argument("--output", required=True, type=Path, help="Destination filename")
    parser.add_argument("--sha256", help="Expected SHA-256 checksum, if supplied by the catalogue")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Network timeout in seconds")
    parser.add_argument("--force", action="store_true", help="Replace an existing destination file")
    parser.add_argument(
        "--data-type",
        choices=sorted(COMMON_PATHS),
        help="Optional product-family hint; does not construct or guess a download URL",
    )
    parser.add_argument(
        "--assembly",
        choices=("GRCh37", "GRCh38"),
        default="GRCh38",
        help="Genome assembly for the optional path hint",
    )
    args = parser.parse_args()

    try:
        if args.data_type:
            print(f"Example catalogue path: {get_common_file_path(args.data_type, args.assembly)}")
        result = download_cosmic_file(
            download_url=args.url,
            output_filename=args.output,
            expected_sha256=args.sha256,
            timeout=args.timeout,
            overwrite=args.force,
        )
    except (ValueError, FileExistsError, IsADirectoryError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"Downloaded: {result['path']}")
    print(f"Bytes: {result['bytes']}")
    print(f"SHA-256: {result['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
