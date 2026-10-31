The ad checker found ads that pass through uBlock Origin with the stock lists and this repository's filter lists.
The check report is in `{report}`: `summary.json` lists the pages, and every page directory holds `report.json`
(found ad elements with their parent chain, ad-related request URLs), `page.png` and `ad-N.png` screenshots.

Update the filter lists in this repository so the ads are hidden or blocked:

- Edit only the `*.txt` filter lists in the repository root. Add rules to the list of the matching site, or create
  a new list with the same header format (`! Title`, `! Description`, `! Homepage`, `! Expires`) and add it to
  `README.md`.
- Prefer cosmetic rules on stable signals: application class names, ad unit IDs such as `R-I-<n>-<n>`,
  `:has()` and `:matches-attr()` procedural filters. Yandex randomizes most class names and IDs, and its
  anti-adblock mode serves ads through first-party proxies (`/_crpd/`, `yastatic.net/naydex/`) that also carry the
  site's own scripts, so do not block those URLs.
- Scope rules to the site (`yandex.*,ya.ru##...`) unless the selector cannot match anything but ads.
- Never hide page content that is not an ad: message lists, editors, menus, search results.
- Verify with `./tools/check_ads.py --output {report}/verify-<n>` (n = 1, 2, ...). It must report 0 ads on every
  page, and the verify `page.png` screenshots must show the page content intact. Repeat until it passes.
- Do not run git commands; the calling script commits and pushes when the final check passes.

Finish with a short summary of the rules you added and why.
