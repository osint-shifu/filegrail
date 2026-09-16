# Brand assets

How to use the brand assets this repository carries.

The lockup at the top of the README, following the reader's theme. The URLs are absolute so that PyPI shows the image too:

```markdown
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-stacked-dark.png">
  <img src="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-stacked-light.png" alt="filegrail" width="220">
</picture>
```

Reach for the PNG anywhere the image leaves this repository. The SVG lockups set the wordmark as live text in Spline Sans Mono, which a reader who does not have the font installed will not see; GitHub and PyPI render an image without loading fonts, so they would show the fallback.

The mark the HTML report shows in its masthead and in its tab icon is not a file: it is drawn in the page by `htmlreport.py`, so a report carries no image to load.

## Files

| File | Use |
| --- | --- |
| `filegrail-stacked-dark.png` `.svg` | vertical lockup, dark backgrounds |
| `filegrail-stacked-light.png` `.svg` | vertical lockup, light backgrounds |
| `filegrail-logo-dark.png` `.svg` | horizontal lockup, dark backgrounds |
| `filegrail-logo-light.png` `.svg` | horizontal lockup, light backgrounds |
| `filegrail-mark.png` `.svg` | mark alone, dark backgrounds |
| `filegrail-mark-light.png` `.svg` | mark alone, light backgrounds |
| `filegrail-mark-ivory.svg` `filegrail-mark-ink.svg` | mark in one colour |
| `filegrail-mark-ivory-accent-star.svg` `filegrail-mark-ink-accent-star.svg` | mark in one colour, diamond in verdigris |

Minimum height for the mark is 16 px, and clear space around it is half its height.
