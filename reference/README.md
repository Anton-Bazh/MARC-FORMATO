# Reference implementation

`marc.py` implements [`.marc` 1.0.0](../SPEC.md) with the Python standard library only (Python 3.8 or later). It applies the same rules as the MARC applications.

| Command | What it does |
|---|---|
| `python3 marc.py validate FILE.marc` | Validates the whole package **without extracting anything** (§5 of the specification) |
| `python3 marc.py info FILE.marc` | Prints the manifest and the list of pages |
| `python3 marc.py extract FILE.marc DIR` | Validates, then extracts both trees overlaid into `DIR`, atomically |
| `python3 marc.py pack FOLDER FILE.marc [--name NAME]` | Creates a package with origin `local` (manifest first, hidden files and symbolic links excluded, already-compressed formats stored) |

Exit code `0` means valid or done; `1` means the package was rejected, with the reason on standard error.

It can also be used as a module:

```python
import marc
manifest, files = marc.inspect("my-wiki.marc")   # raises marc.InvalidMarc if not valid
```

Tests: `python3 -m unittest -v test_marc.py`.

License: [MIT](../LICENSE).
