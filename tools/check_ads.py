#!/usr/bin/python3
"""Check pages for ads that pass through uBlock Origin with the stock lists and this repository's lists.

Firefox runs with a dedicated persistent profile, so a Yandex login made once with ``--login`` is reused by later
headless runs. Each run copies the repository lists into uBlock Origin's "My filters", loads every page from the
pages file, looks for visible ads and writes a report with screenshots. The exit code is 1 when an ad is found.
"""

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

REPO = Path(__file__).resolve().parent.parent
# Snap Firefox can only use profiles outside hidden directories of the home folder.
DATA = Path.home() / 'snap' / 'firefox' / 'common' / 'adblock-check'
PROFILE = DATA / 'profile'
XPI = DATA / 'ublock-origin.xpi'
REPORTS = Path.home() / '.local' / 'state' / 'adblock-check' / 'reports'
XPI_URL = 'https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi'
UBO_ID = 'uBlock0@raymondhill.net'
UBO_UUID = '5d1b6a1e-7c55-4d6b-9a3e-ad0b10c4e001'
FIREFOX = '/snap/firefox/current/usr/lib/firefox/firefox'
GECKODRIVER = '/snap/bin/geckodriver'

FIND_ADS_JS = r"""
const unitId = /(?:^|_)R-[AI]-\d+-\d+$/;
const labels = /^(реклама|ad|ads|social ad|социальная реклама)$/i;
const adImage = /avatars\.mds\.yandex\.net\/get-direct|\/_crpd\//;
const visible = e => {
    const r = e.getBoundingClientRect();
    const s = getComputedStyle(e);
    return r.width >= 20 && r.height >= 20 && s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
};
const describe = e => e.tagName + (e.id ? '#' + e.id : '') +
    (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\s+/).join('.') : '');
const chain = e => {
    const out = [];
    for (; e && out.length < 14; e = e.parentElement) {
        out.push(describe(e));
    }
    return out;
};
const found = new Map();
const add = (e, reason) => {
    if (!found.has(e)) {
        found.set(e, new Set());
    }
    found.get(e).add(reason);
};
for (const e of document.querySelectorAll('[id]')) {
    if ((unitId.test(e.id) || e.id.startsWith('yandex_rtb_')) && visible(e)) {
        add(e, 'ad unit id');
    }
}
for (const e of document.querySelectorAll('iframe')) {
    if (/safeframe|\/ads\/|an\.yandex/.test(e.src || '') && visible(e)) {
        add(e, 'ad iframe');
    }
}
for (const e of document.querySelectorAll('img')) {
    if (adImage.test(e.currentSrc || e.src || '') && e.width >= 60 && e.height >= 60 && visible(e)) {
        add(e.parentElement?.parentElement || e, 'ad image');
    }
}
const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const e = n.parentElement;
    if (e && labels.test(n.textContent.trim()) && e.offsetWidth > 0 && e.offsetHeight > 0) {
        let box = e;
        while (box.parentElement && box.parentElement !== document.body &&
               box.getBoundingClientRect().width * box.getBoundingClientRect().height < 30000) {
            box = box.parentElement;
        }
        add(box, 'ad label');
    }
}
const items = [];
for (const [e, reasons] of found) {
    // Report only the outermost element of nested findings.
    if ([...found.keys()].some(o => o !== e && o.contains(e))) {
        continue;
    }
    const r = e.getBoundingClientRect();
    e.setAttribute('data-adcheck', String(items.length));
    items.push({
        reasons: [...reasons],
        rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
        chain: chain(e),
        text: (e.innerText || '').trim().slice(0, 200),
    });
}
const resources = performance.getEntriesByType('resource').map(r => r.name)
    .filter(n => /\/_crpd\/|\/naydex\/|\/an\/(count|rtbcount)|\/ads\/(meta|system)|safeframe|partner-code/.test(n));
return {items, resources: [...new Set(resources.map(n => n.slice(0, 160)))]};
"""


def start_firefox(headless: bool) -> webdriver.Firefox:
    """Start Firefox with the dedicated persistent profile.

    :param headless: run without a window
    :return: WebDriver session
    """
    PROFILE.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.binary_location = FIREFOX
    options.add_argument('-profile')
    options.add_argument(str(PROFILE))
    if headless:
        options.add_argument('-headless')

    options.set_preference('extensions.webextensions.uuids', json.dumps({UBO_ID: UBO_UUID}))
    driver = webdriver.Firefox(options=options, service=Service(GECKODRIVER, service_args=['--allow-system-access']))
    driver.set_window_size(1536, 1100)
    if not XPI.exists():
        urllib.request.urlretrieve(XPI_URL, XPI)

    driver.install_addon(str(XPI))

    return driver


def open_extension_page(driver: webdriver.Firefox, page: str) -> None:
    """Open a uBlock Origin dashboard page, which WebDriver cannot navigate to directly.

    :param driver: webdriver.Firefox session
    :param page: dashboard page file name
    """
    with driver.context(driver.CONTEXT_CHROME):
        driver.execute_script(
            """gBrowser.selectedBrowser.loadURI(Services.io.newURI(arguments[0]),
                {triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal()});""",
            f'moz-extension://{UBO_UUID}/{page}',
        )
    time.sleep(3)


def load_filters(driver: webdriver.Firefox, lists: list[Path]) -> int:
    """Replace uBlock Origin's "My filters" with the repository lists.

    :param driver: webdriver.Firefox session
    :param lists: filter list files
    :return: number of lines written
    """
    text = '\n'.join(path.read_text() for path in lists)
    open_extension_page(driver, '1p-filters.html')
    result = driver.execute_script(
        """const cm = document.querySelector('.CodeMirror').CodeMirror;
        cm.setValue(arguments[0]);
        document.querySelector('#userFiltersApply').click();
        return cm.lineCount();""",
        text,
    )
    time.sleep(3)

    return int(result)


def check_page(driver: webdriver.Firefox, url: str, out: Path, wait: float) -> dict[str, Any]:
    """Load a page, find visible ads and save screenshots.

    :param driver: webdriver.Firefox session
    :param url: page URL
    :param out: directory for this page's files
    :param wait: seconds to wait after load
    :return: page report
    """
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {'url': url}
    try:
        driver.get(url)
    except WebDriverException as error:
        report['error'] = str(error).splitlines()[0]

    time.sleep(wait)
    report['final_url'] = driver.current_url
    report['title'] = driver.title
    report.update(driver.execute_script(FIND_ADS_JS))
    driver.save_screenshot(str(out / 'page.png'))
    for index, item in enumerate(report['items']):
        try:
            element = driver.find_element('css selector', f'[data-adcheck="{index}"]')
            element.screenshot(str(out / f'ad-{index}.png'))
        except WebDriverException as error:
            item['screenshot_error'] = str(error).splitlines()[0]

    (out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')

    return report


def main() -> int:
    """Run the checker.

    :return: exit code
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--login', action='store_true', help='open a window to log in to sites, then wait for close')
    parser.add_argument('--pages', type=Path, default=REPO / 'tools' / 'pages.txt', help='file with one URL per line')
    parser.add_argument('--lists', type=Path, nargs='*', default=sorted(REPO.glob('*.txt')), help='filter lists')
    parser.add_argument('--wait', type=float, default=12, help='seconds to wait after each page load')
    parser.add_argument('--output', type=Path, help='report directory (default: timestamped under ~/.local/state)')
    args = parser.parse_args()
    pages = [line.strip() for line in args.pages.read_text().splitlines() if line.strip() and line[0] != '#']

    if args.login:
        driver = start_firefox(headless=False)
        driver.get(pages[0] if pages else 'https://passport.yandex.ru/')
        print('Log in in the Firefox window, then close it.')
        try:
            while driver.window_handles:
                time.sleep(1)

        except WebDriverException:
            pass

        return 0

    out = args.output or REPORTS / datetime.now().strftime('%Y%m%d-%H%M%S')
    driver = start_firefox(headless=True)
    try:
        # Give uBlock Origin time to load its lists in a new profile.
        time.sleep(10)
        lines = load_filters(driver, args.lists)
        reports = [check_page(driver, url, out / f'{n:02d}', args.wait) for n, url in enumerate(pages)]
    finally:
        driver.quit()

    summary: dict[str, Any] = {
        'filter_lines': lines,
        'pages': [
            {'url': r['url'], 'final_url': r['final_url'], 'ads': len(r['items']), 'error': r.get('error')}
            for r in reports
        ],
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    print(f'Report: {out}')

    return 1 if any(p['ads'] for p in summary['pages']) else 0


if __name__ == '__main__':
    sys.exit(main())
