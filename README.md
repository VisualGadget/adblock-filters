# adblock-filters

Custom filter lists for uBlock Origin (most rules also work in AdGuard).

| List | Covers | Subscribe URL |
| --- | --- | --- |
| [filters.txt](filters.txt) | All lists, one section per company. Yandex: Translate sidebar ads, Yandex Mail ads and promo buttons, ya.ru feed, Yandex RTB units on any site. Ozon: survey panels | `https://raw.githubusercontent.com/VisualGadget/adblock-filters/main/filters.txt` |

## Usage

uBlock Origin → Dashboard → **Filter lists** → **Custom** → **Import**, paste the subscribe URL, then **Apply changes**.

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
