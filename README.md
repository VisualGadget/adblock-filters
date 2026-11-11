# adblock-filters

Custom filter lists for uBlock Origin (most rules also work in AdGuard).

| List | Covers | Subscribe URL |
| --- | --- | --- |
| [filters.txt](filters.txt) | All lists, one section per company. Yandex: Translate sidebar ads, Yandex Mail ads and promo buttons, ya.ru feed, Yandex RTB units on any site. Ozon: survey panels | `https://raw.githubusercontent.com/VisualGadget/adblock-filters/main/filters.txt` |

## Usage

uBlock Origin → Dashboard → **Filter lists** → **Custom** → **Import**, paste the subscribe URL, then **Apply changes**.

## Firefox extension

`extension/` holds fixes that filter lists cannot do, as a Firefox extension:

- Fastpic: an image link such as `i123.fastpic.org/big/…/hash.jpg` opens as the bare image instead of the
  `fastpic.org/view/` ad page. The image server redirects page loads by the `Sec-Fetch-Dest` and `Accept` request
  headers, so the extension asks for an image there.
- Fastpic: a view page (`fastpic.org/view/…html`) is replaced with its full size image, taken from the page behind
  its "go to image" button. This also covers protected images (file names starting with `_`) that the image server
  always redirects to the view page.
- Fastpic: the popunder on `fastpic.org/view/` pages is blocked. It sends the current tab to an ad on the first click,
  which leaves ad pages in the tab history.

Install the signed `.xpi` from the latest `extension-v*` release; installed copies update themselves from
`extension/updates.json`. To try a change without signing, open `about:debugging#/runtime/this-firefox` →
**Load Temporary Add-on** and pick `extension/manifest.json`.

To release a change, bump `version` in `extension/manifest.json` and run `tools/release_extension.sh` with AMO API
credentials in `WEB_EXT_API_KEY` and `WEB_EXT_API_SECRET` or in `~/.config/secrets/tokens.yaml`, then commit and push
`extension/updates.json`:

```yaml
amo:
  api_key: user:12345678:123  # JWT issuer
  api_secret: ...             # JWT secret
```

## Automatic check

`tools/check_ads.py` opens the pages from `tools/pages.txt` in headless Firefox with uBlock Origin, the stock lists
and these lists, and reports ads that are still visible. It uses a dedicated persistent profile in
`~/snap/firefox/common/adblock-check/`; log in to sites once with `tools/check_ads.py --login`.

`tools/auto_update.sh` runs the check daily from a systemd user timer. When ads get through, Claude Code updates
the lists, the check runs again, and the change is pushed only when no ads are left. Reports are kept outside the
repository in `~/.local/state/adblock-check/reports/`.

```bash
ln -sf "$PWD"/tools/systemd/adblock-check.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now adblock-check.timer
```
