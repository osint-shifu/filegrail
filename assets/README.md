# Brand assets

Construction rules and the colour meanings live in [`DESIGN.md`](../docs/DESIGN.md).
This file is how to use them.

Banner at the top of the README (absolute URL, so PyPI shows it too):

```markdown
<img src="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-banner.png" alt="filegrail" width="820">
```

Lockup that follows the reader's theme:

```markdown
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/filegrail-logo-dark.svg">
    <img src="assets/filegrail-logo-light.svg" alt="filegrail" width="300">
  </picture>
</p>
```

Mark only (docs, favicon, social avatar):

```markdown
<img src="assets/filegrail-mark.svg" alt="" width="64">
```

## Files

| File | Use |
| --- | --- |
| `filegrail-banner.png` | 2560x1280 README header and social preview |
| `filegrail-banner.svg` | 1280x360 header, vector |
| `filegrail-logo-dark.svg` | horizontal lockup, dark backgrounds |
| `filegrail-logo-light.svg` | horizontal lockup, light backgrounds |
| `filegrail-mark.svg` | square mark, dark backgrounds / favicon |
| `filegrail-mark-light.svg` | square mark, light backgrounds |
| `filegrail-mark-mono.svg` | single-colour mark for one-colour contexts |
