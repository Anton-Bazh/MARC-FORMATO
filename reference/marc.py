#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Antonio Baeza
"""Reference implementation of the .marc format 1.0.0 (see SPEC.md).

Standard library only (Python 3.8+). It follows the same rules as the MARC applications:

    python3 marc.py validate wiki.marc          # validate without extracting anything
    python3 marc.py info wiki.marc              # manifest and page list
    python3 marc.py extract wiki.marc out-dir   # validate, then extract (atomic)
    python3 marc.py pack folder wiki.marc [--name "My wiki"]

Exit code 0 means valid / done; 1 means the package was rejected (the reason is printed).
"""
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

FORMAT_VERSION = "1.0.0"
MANIFEST = "manifest.json"
CONTENT, ASSETS = "content", "assets"
MARKDOWN = {"md", "markdown"}
# Already-compressed formats are stored without recompression (identical bytes).
STORED = {"png", "jpg", "jpeg", "gif", "webp", "avif", "heic", "jxl", "pdf", "zip", "gz", "xz", "bz2", "7z", "zst",
          "mp4", "mov", "webm", "mkv", "mp3", "ogg", "opus", "m4a", "flac", "woff", "woff2", "docx", "xlsx", "pptx",
          "odt", "ods", "odp"}
MAX_ENTRIES = 200_000
MAX_TOTAL = 64 * 1024 ** 3   # 64 GiB uncompressed
MAX_RATIO = 200              # for entries larger than 1 MiB
FIELDS = ["version_formato", "nombre_proyecto", "tipo_origen", "repositorio_url", "rama", "ultimo_commit", "fecha_empaquetado"]

_CREDENTIALS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?<![A-Za-z0-9_])bearer\s+[A-Za-z0-9._-]{10,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


class InvalidMarc(Exception):
    """The package does not follow the specification; the message says why."""


def looks_like_credential(value: str) -> bool:
    return any(p.search(value) for p in _CREDENTIALS)


def validate_manifest(m) -> None:
    if not isinstance(m, dict):
        raise InvalidMarc("manifest.json is not a JSON object.")
    version = m.get("version_formato")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise InvalidMarc("manifest.json has no valid 'version_formato'.")
    if version.split(".")[0] != FORMAT_VERSION.split(".")[0]:
        raise InvalidMarc(f"This .marc uses format {version}; this reader supports {FORMAT_VERSION.split('.')[0]}.x.")
    name = m.get("nombre_proyecto")
    if not isinstance(name, str) or not name.strip():
        raise InvalidMarc("manifest.json has no 'nombre_proyecto'.")
    origin = m.get("tipo_origen")
    if origin == "git":
        for k in ("repositorio_url", "rama", "ultimo_commit"):
            if not isinstance(m.get(k), str) or not m[k]:
                raise InvalidMarc(f"A .marc with origin 'git' must set '{k}'.")
    elif origin != "local":
        raise InvalidMarc("'tipo_origen' must be 'git' or 'local'.")
    if not isinstance(m.get("fecha_empaquetado"), str):
        raise InvalidMarc("manifest.json has no 'fecha_empaquetado'.")
    for k, v in m.items():
        if isinstance(v, str):
            if looks_like_credential(v):
                raise InvalidMarc(f"Field '{k}' looks like a credential; a .marc never carries tokens or keys.")
            if k == "repositorio_url" and "://" in v and "@" in v.split("://", 1)[1].split("/", 1)[0]:
                raise InvalidMarc("The repository URL includes a user or password; a .marc never carries credentials.")


def safe_parts(name: str):
    """Path components of a ZIP entry, or InvalidMarc if it could escape the destination folder."""
    if not name or "\\" in name or "\0" in name:
        raise InvalidMarc(f"Invalid path inside the .marc: {name!r}.")
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise InvalidMarc(f"The .marc contains an absolute path: {name!r}.")
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if not parts or ".." in parts:
        raise InvalidMarc(f"The .marc tries to write outside its folder: {name!r}.")
    return parts


def inspect(path):
    """Validate the whole package WITHOUT extracting anything. Returns (manifest, file entries)."""
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        raise InvalidMarc("The file is not a valid .marc (not a ZIP).")
    with z:
        infos = z.infolist()
        if len(infos) > MAX_ENTRIES:
            raise InvalidMarc(f"The .marc has too many entries ({len(infos)}).")
        total, seen, files, overlay, has_manifest = 0, set(), [], {}, False
        for info in infos:
            parts = safe_parts(info.filename)
            top = parts[0]
            if info.is_dir():
                if top not in (CONTENT, ASSETS):
                    raise InvalidMarc(f"Folder not allowed in a .marc: {info.filename!r}.")
                continue
            is_manifest = info.filename == MANIFEST
            if not (is_manifest or top in (CONTENT, ASSETS)) or (len(parts) == 1 and not is_manifest):
                raise InvalidMarc(f"Entry not allowed in a .marc: {info.filename!r}.")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise InvalidMarc(f"The .marc contains a symbolic link: {info.filename!r}.")
            size, comp = info.file_size, info.compress_size
            if size > 1024 * 1024 and comp > 0 and size // comp > MAX_RATIO:
                raise InvalidMarc(f"Suspicious compression in {info.filename!r} (possible decompression bomb).")
            total += size
            if total > MAX_TOTAL:
                raise InvalidMarc("The uncompressed content exceeds the maximum allowed size.")
            key = "/".join(parts).lower()
            if key in seen:
                raise InvalidMarc(f"Duplicate entry in the .marc: {info.filename!r}.")
            seen.add(key)
            if is_manifest:
                has_manifest = True
            else:
                rel = "/".join(parts[1:]).lower()
                if rel in overlay:
                    raise InvalidMarc(f"'{'/'.join(parts[1:])}' appears in both content/ and assets/.")
                overlay[rel] = info.filename
                files.append(info)
        if not has_manifest:
            raise InvalidMarc("The .marc has no manifest.json.")
        try:
            manifest = json.loads(z.read(MANIFEST).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise InvalidMarc(f"manifest.json is not valid JSON: {e}")
        validate_manifest(manifest)
        return manifest, files


def extract(path, dest) -> dict:
    """Validate, then extract both trees overlaid into `dest` (atomic: a temporary folder is renamed at the end)."""
    manifest, files = inspect(path)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{dest.name}-", dir=dest.parent))
    try:
        root = staging.resolve()
        with zipfile.ZipFile(path) as z:
            for info in files:
                out = staging.joinpath(*safe_parts(info.filename)[1:])
                out.parent.mkdir(parents=True, exist_ok=True)
                if root not in out.parent.resolve().parents and out.parent.resolve() != root:
                    raise InvalidMarc(f"Path outside the extraction folder: {info.filename!r}.")
                with z.open(info) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        if dest.exists():
            raise InvalidMarc(f"Destination already exists: {dest}.")
        staging.rename(dest)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def _source_files(root: Path):
    """Files to pack: hidden files and folders, symbolic links and other .marc are always excluded."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        dirnames[:] = sorted(n for n in dirnames if not n.startswith(".") and not (d / n).is_symlink())
        for n in sorted(filenames):
            p = d / n
            if n.startswith(".") or n.lower().endswith(".marc") or p.is_symlink():
                continue
            out.append(p)
    return out


def pack(folder, dest, name=None) -> Path:
    """Create a .marc (origin 'local') from a folder. The manifest is the first ZIP entry."""
    folder, dest = Path(folder), Path(dest)
    manifest = {
        "version_formato": FORMAT_VERSION,
        "nombre_proyecto": name or folder.resolve().name,
        "tipo_origen": "local", "repositorio_url": None, "rama": None, "ultimo_commit": None,
        "fecha_empaquetado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    validate_manifest(manifest)
    tmp = dest.with_name(f".{dest.name}.tmp")
    with zipfile.ZipFile(tmp, "w", allowZip64=True) as z:
        z.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", zipfile.ZIP_DEFLATED)
        for p in _source_files(folder):
            rel = p.relative_to(folder).as_posix()
            ext = p.suffix.lower().lstrip(".")
            tree = CONTENT if ext in MARKDOWN else ASSETS
            method = zipfile.ZIP_STORED if ext in STORED else zipfile.ZIP_DEFLATED
            z.write(p, f"{tree}/{rel}", compress_type=method)
    inspect(tmp)  # never leave behind a package that this same reader would reject
    tmp.replace(dest)
    return dest


def main(argv) -> int:
    if len(argv) < 2 or argv[0] not in ("validate", "info", "extract", "pack"):
        print(__doc__.strip())
        return 2
    try:
        cmd = argv[0]
        if cmd == "validate":
            m, files = inspect(argv[1])
            print(f"valid · format {m['version_formato']} · {m['nombre_proyecto']} · {len(files)} files")
        elif cmd == "info":
            m, files = inspect(argv[1])
            print(json.dumps({k: m.get(k) for k in FIELDS}, ensure_ascii=False, indent=2))
            for f in files:
                if f.filename.startswith(CONTENT + "/"):
                    print("page:", f.filename[len(CONTENT) + 1:])
        elif cmd == "extract":
            if len(argv) < 3:
                raise InvalidMarc("usage: marc.py extract wiki.marc out-dir")
            m = extract(argv[1], argv[2])
            print(f"extracted '{m['nombre_proyecto']}' into {argv[2]}")
        elif cmd == "pack":
            if len(argv) < 3:
                raise InvalidMarc("usage: marc.py pack folder wiki.marc [--name NAME]")
            name = argv[argv.index("--name") + 1] if "--name" in argv else None
            print("created", pack(argv[1], argv[2], name))
        return 0
    except InvalidMarc as e:
        print(f"rejected: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
