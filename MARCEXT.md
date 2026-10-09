# `.marcext` extensions — planned

**Status: not specified yet.** Nothing in this file is a stable rule.

`.marcext` will be the format for **local, offline extensions** of MARC: interface languages, rendering engines, document templates and, later, security profiles from institutions (formats of certificates and keys, trust roots, validation rules) so that MARC can sign and verify documents with them.

Design principles already agreed:

| Principle | Meaning |
|---|---|
| Offline | Extensions are installed from files and run without network access |
| Declarative where security matters | A security extension declares data and rules; MARC's core executes them. An extension never reads private keys and cannot weaken algorithms or skip checks |
| Signed | MARC shows who signed an extension: the institution (official), the community (reviewed) or nobody (unverified, with a warning) |
| Permissive licenses | Extensions distributed through this repository use permissive licenses |

Open questions are tracked in the [issues](../../issues). Proposals are welcome.
