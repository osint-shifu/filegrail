# Brand assets

Construction rules and the colour meanings live in [`DESIGN.md`](../docs/DESIGN.md). This file is how to use them.

Banner at the top of the README (absolute URL, so PyPI shows it too):

```markdown
<img src="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-banner.png" alt="filegrail" width="100%">
```

The same image is what GitHub takes as the repository's social preview, under Settings, General, Social preview.

The mark the HTML report shows in its masthead and in its tab icon is not a file: it is drawn in the page by `htmlreport.py`, so a report carries no image to load.

## Files

| File | Use |
| --- | --- |
| `filegrail-banner.png` | 2560x1280 README header and social preview |
