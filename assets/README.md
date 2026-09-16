# Brand assets

How to use the brand assets this repository carries.

The lockup at the top of the README, following the reader's theme. The URLs are absolute so that PyPI shows the image too:

```markdown
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-logo-dark.png">
  <img src="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-logo-light.png" alt="filegrail" width="380">
</picture>
```

The banner is not used in the README. It is what GitHub takes as the repository's social preview, uploaded by hand under Settings, General, Social preview, where 1280x640 is the size to give it.

The mark the HTML report shows in its masthead and in its tab icon is not a file: it is drawn in the page by `htmlreport.py`, so a report carries no image to load.

## Files

| File | Use |
| --- | --- |
| `filegrail-logo-dark.png` | horizontal lockup, dark backgrounds |
| `filegrail-logo-light.png` | horizontal lockup, light backgrounds |
| `filegrail-banner.png` | 2560x1280 social preview |
