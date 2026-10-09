# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Antonio Baeza
"""Tests for the reference implementation:  python3 -m unittest -v test_marc.py"""
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

import marc

GOOD = {"version_formato": "1.0.0", "nombre_proyecto": "Test", "tipo_origen": "local",
        "repositorio_url": None, "rama": None, "ultimo_commit": None, "fecha_empaquetado": "2026-10-09T00:00:00Z"}


def build(path, entries, manifest=GOOD):
    """entries: list of (name, bytes) or (name, bytes, external_attr)."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        if manifest is not None:
            z.writestr("manifest.json", json.dumps(manifest))
        for e in entries:
            info = zipfile.ZipInfo(e[0])
            if len(e) > 2:
                info.external_attr = e[2]
            z.writestr(info, e[1], zipfile.ZIP_DEFLATED)
    return path


class Reference(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def rejected(self, entries, manifest=GOOD, text=""):
        p = build(self.tmp / "x.marc", entries, manifest)
        with self.assertRaises(marc.InvalidMarc) as c:
            marc.inspect(p)
        self.assertIn(text, str(c.exception))

    def test_valid_local(self):
        p = build(self.tmp / "ok.marc", [("content/00 Home.md", b"# Home\n"), ("assets/img/a.png", b"\x89PNG")])
        m, files = marc.inspect(p)
        self.assertEqual(m["nombre_proyecto"], "Test")
        self.assertEqual(len(files), 2)

    def test_valid_git(self):
        m = dict(GOOD, tipo_origen="git", repositorio_url="https://github.com/team/wiki.git", rama="main", ultimo_commit="abc123")
        marc.inspect(build(self.tmp / "git.marc", [("content/a.md", b"a")], m))

    def test_git_requires_fields(self):
        self.rejected([("content/a.md", b"a")], dict(GOOD, tipo_origen="git"), "must set")

    def test_other_major_version(self):
        self.rejected([("content/a.md", b"a")], dict(GOOD, version_formato="2.0.0"), "supports 1.x")

    def test_missing_manifest(self):
        self.rejected([("content/a.md", b"a")], None, "no manifest.json")

    def test_credentials(self):
        m = dict(GOOD, nombre_proyecto="ghp_" + "A" * 30)
        self.rejected([("content/a.md", b"a")], m, "credential")
        m = dict(GOOD, tipo_origen="git", repositorio_url="https://user:pass@github.com/t/w.git", rama="main", ultimo_commit="a")
        self.rejected([("content/a.md", b"a")], m, "user or password")

    def test_zip_slip(self):
        self.rejected([("content/../../evil.md", b"x")], text="outside")
        self.rejected([("/etc/passwd", b"x")], text="absolute")
        self.rejected([("C:/evil.md", b"x")], text="absolute")

    def test_entries_outside_the_trees(self):
        self.rejected([("readme.txt", b"x")], text="not allowed")
        self.rejected([("other/a.md", b"x")], text="not allowed")

    def test_symlink(self):
        self.rejected([("assets/link", b"/etc/passwd", (0o120777 << 16))], text="symbolic link")

    def test_same_path_in_both_trees(self):
        self.rejected([("content/a.md", b"a"), ("assets/a.md", b"b")], text="both content/ and assets/")

    def test_duplicates(self):
        self.rejected([("content/a.md", b"a"), ("content/A.md", b"b")], text="Duplicate")

    def test_decompression_bomb(self):
        self.rejected([("assets/zeros.bin", b"\0" * (8 * 1024 * 1024))], text="decompression bomb")

    def test_pack_extract_roundtrip(self):
        src = self.tmp / "wiki"
        (src / "img").mkdir(parents=True)
        (src / ".git").mkdir()
        (src / "00 Home.md").write_bytes(b"# Home\n\n![](img/a.png)\n")
        (src / "img" / "a.png").write_bytes(b"\x89PNG\r\n")
        (src / ".env").write_text("SECRET=1")
        (src / ".git" / "config").write_text("x")
        out = marc.pack(src, self.tmp / "wiki.marc", "Wiki")
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
        self.assertEqual(names[0], "manifest.json", "the manifest goes first")
        self.assertEqual(sorted(names[1:]), ["assets/img/a.png", "content/00 Home.md"], "hidden files are excluded")
        marc.extract(out, self.tmp / "out")
        self.assertEqual((self.tmp / "out" / "00 Home.md").read_bytes(), b"# Home\n\n![](img/a.png)\n", "Markdown is byte-identical")
        self.assertTrue((self.tmp / "out" / "img" / "a.png").exists(), "the trees are overlaid")


if __name__ == "__main__":
    unittest.main()
