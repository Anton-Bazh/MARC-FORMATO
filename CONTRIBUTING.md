# Contributing

Thank you for helping with MARC's open formats.

## What you can contribute

| Contribution | How |
|---|---|
| A question or an unclear part of the specification | Open an issue with the *Specification question* template |
| An error in the specification or in the reference implementation | Open an issue with the *Bug report* template, with a sample `.marc` if possible |
| A change to a format | Open an issue with the *Format proposal* template **before** sending a pull request |
| A fix to the reference implementation | Pull request, with a test in `reference/test_marc.py` |
| An implementation in another language or tool | Open an issue so we can link it from the README |

## Rules for format changes

- Compatible changes (new optional fields, clarifications) increase the **minor** or **patch** version.
- Incompatible changes increase the **major** version and need a strong reason: every `.marc` already shared depends on the format.
- A `.marc` must never be able to carry credentials or write outside its folder. Changes that weaken §3 or §5 of the specification are not accepted.

## Language

Issues and pull requests in **English** are preferred so that everyone can follow them; Spanish is also welcome.

## License of contributions

By contributing you agree that your contribution is published under the license of the part you change: CC BY 4.0 for specifications and documentation, MIT for code.
