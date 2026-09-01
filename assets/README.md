# Brand assets

Construction rules and the colour meanings live in [`DESIGN.md`](../DESIGN.md).
This file is how to use them.

Banner (works on both GitHub themes):

```markdown
<p align="center">
  <img src="assets/filetrail-banner.svg" alt="filetrail — trace origins, extract metadata" width="820">
</p>
```

Lockup that follows the reader's theme:

```markdown
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/filetrail-logo-dark.svg">
    <img src="assets/filetrail-logo-light.svg" alt="filetrail" width="300">
  </picture>
</p>
```

Mark only (docs, favicon, social avatar):

```markdown
<img src="assets/filetrail-mark.svg" alt="" width="64">
```

## Files

| File | Use |
| --- | --- |
| `filetrail-banner.svg` | 1280x360 README header |
| `filetrail-logo-dark.svg` | horizontal lockup, dark backgrounds |
| `filetrail-logo-light.svg` | horizontal lockup, light backgrounds |
| `filetrail-mark.svg` | square mark, dark backgrounds / favicon |
| `filetrail-mark-light.svg` | square mark, light backgrounds |
| `filetrail-mark-mono.svg` | single-colour mark for one-colour contexts |
