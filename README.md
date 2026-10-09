# MARC-FORMATO

The open file formats of **MARC** — *Markdown Automatizado por Repo y Consulta* — and the place where the community discusses them.

MARC is a reader and editor for technical documentation written in Markdown (Obsidian-style wikilinks, callouts, Mermaid, math, charts, interactive diagrams). It works on Git repositories, local folders and `.marc` packages, offline, on Linux, Windows and Android.

| | |
|---|---|
| [`SPEC.md`](SPEC.md) | **`.marc` format 1.0.0** — a whole wiki in one portable file (ZIP + manifest) |
| [`MARCEXT.md`](MARCEXT.md) | `.marcext` extensions — planned, not specified yet |
| [`reference/`](reference/) | Reference implementation in Python (standard library only): validate, inspect, extract and create `.marc` files |
| [Issues](../../issues) | Questions, bugs in the specification and proposals |

## Get MARC

The **Linux installer** (`.deb`, for Debian, Ubuntu and derivatives) is attached to the [Releases](../../releases) of this repository:

```bash
sudo apt install ./marc_2.3.0_amd64.deb
```

It installs MARC E (desktop edition) in `/opt/marc` and registers it to open `.marc` and `.md` files.

## Quick start with the reference implementation

```bash
python3 reference/marc.py validate my-wiki.marc      # check a package without extracting it
python3 reference/marc.py info my-wiki.marc          # manifest and pages
python3 reference/marc.py extract my-wiki.marc out/  # safe, atomic extraction
python3 reference/marc.py pack my-folder my-wiki.marc --name "My wiki"
```

## Related repositories

| Repository | What it is |
|---|---|
| [MARC-DOC](https://github.com/Anton-Bazh/MARC-DOC) | User documentation (Spanish), synced inside the apps |
| [MARC-DOC-TRADUCCIONES](https://github.com/Anton-Bazh/MARC-DOC-TRADUCCIONES) | Community translations of the user documentation |

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Issues and pull requests are welcome in **English** (Spanish is also fine). Please follow the [code of conduct](CODE_OF_CONDUCT.md).

## License

| What | License |
|---|---|
| Specifications (`SPEC.md`, `MARCEXT.md`) and documentation | [Creative Commons Attribution 4.0 International](LICENSE-SPEC) (CC BY 4.0) |
| Code in `reference/` | [MIT](LICENSE) |

You may implement the formats in any software, open or closed, without asking for permission.
