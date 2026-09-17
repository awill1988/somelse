#!/usr/bin/env python3
"""Idempotently fetch and verify model weights and llama-cli runner binary."""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "adversarial-reviewer"


def load_env(env_path: Path) -> dict:
    values = {}
    with open(env_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip()
    return values


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def download_file(urls: list, dest_path: Path, expected_sha256: str = None) -> bool:
    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    for url in urls:
        if not url:
            continue
        print(f"attempting download from {url}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "somelse-adversarial-reviewer/1.0"})
            with urllib.request.urlopen(req, timeout=60) as response, open(temp_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

            if expected_sha256:
                actual_sha256 = compute_sha256(temp_path)
                if actual_sha256.lower() != expected_sha256.lower():
                    print(f"checksum mismatch: expected {expected_sha256}, got {actual_sha256}", file=sys.stderr)
                    if temp_path.exists():
                        temp_path.unlink()
                    continue

            temp_path.rename(dest_path)
            print(f"successfully downloaded and verified {dest_path.name}")
            return True
        except Exception as error:
            print(f"download failed for {url}: {error}", file=sys.stderr)
            if temp_path.exists():
                temp_path.unlink()

    return False


def ensure_model(cache_dir: Path, config: dict) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_name = config["MODEL_NAME"]
    expected_sha256 = config["MODEL_SHA256"]
    model_path = cache_dir / model_name

    if model_path.exists():
        actual_sha256 = compute_sha256(model_path)
        if actual_sha256.lower() == expected_sha256.lower():
            print(f"model {model_name} already present and verified in cache.")
            return model_path
        print(f"cached model checksum invalid, refetching...")
        model_path.unlink()

    urls = [config.get("PRIMARY_MODEL_URL"), config.get("FALLBACK_MODEL_URL")]
    if not download_file(urls, model_path, expected_sha256):
        raise RuntimeError(f"failed to download valid model {model_name} from all available sources.")

    return model_path


def ensure_runner(cache_dir: Path, config: dict) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    runner_dir = cache_dir / "llama_runner"

    # Check for already extracted binary
    found_binaries = list(runner_dir.glob("**/llama-cli")) + list(runner_dir.glob("**/llama-cli.exe"))
    if found_binaries and os.access(found_binaries[0], os.X_OK):
        print(f"llama-cli runner already present and executable at {found_binaries[0]}")
        return found_binaries[0]

    runner_url = config.get("LLAMA_RUNNER_URL")
    if not runner_url:
        print("no LLAMA_RUNNER_URL specified, skipping runner download.")
        return runner_dir / "llama-cli"

    zip_path = cache_dir / "llama-runner.zip"
    if not download_file([runner_url], zip_path):
        raise RuntimeError(f"failed to download runner from {runner_url}")

    print("extracting full runner package from archive...")
    runner_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(runner_dir)

    if zip_path.exists():
        zip_path.unlink()

    found_binaries = list(runner_dir.glob("**/llama-cli")) + list(runner_dir.glob("**/llama-cli.exe"))
    if not found_binaries:
        raise RuntimeError("could not find llama-cli binary in downloaded runner archive.")

    actual_bin = found_binaries[0].resolve()
    actual_bin.chmod(0o755)

    # Ensure shared libraries in that directory are readable/executable and symlink them to cache_dir
    for lib in actual_bin.parent.glob("*.so*"):
        try:
            lib.chmod(0o755)
            dest_lib = cache_dir / lib.name
            if dest_lib.is_symlink() or dest_lib.exists():
                dest_lib.unlink()
            dest_lib.symlink_to(lib.resolve())
        except Exception:
            pass

    # Create top-level symlink for backwards compatibility
    top_link = cache_dir / "llama-cli"
    try:
        if top_link.is_symlink() or top_link.exists():
            top_link.unlink()
        top_link.symlink_to(actual_bin)
    except Exception:
        pass

    print(f"llama-cli installed to {actual_bin}")
    return actual_bin


def main():
    parser = argparse.ArgumentParser(description="Ensure model weights and llama runner are cached.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="Directory to cache models and binaries")
    parser.add_argument("--env-file", type=Path, default=SCRIPT_DIR / "model.env", help="Path to model.env configuration")
    parser.add_argument("--model-only", action="store_true", help="Download only the model weights, skip runner")
    args = parser.parse_args()

    config = load_env(args.env_file)
    ensure_model(args.cache_dir, config)
    if not args.model_only:
        try:
            ensure_runner(args.cache_dir, config)
        except Exception as err:
            print(f"note: runner download skipped or failed ({err}); local system runner may be used if present.")


if __name__ == "__main__":
    main()
