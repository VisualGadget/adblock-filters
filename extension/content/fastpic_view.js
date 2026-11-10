// Fastpic view page (fastpic.org/view/.../<hash>.jpg.html): replace it with the full size image. The page shows the
// image only behind a "go to image" link with a one-time token; the image address is taken from that linked page, so
// no rule about how image addresses are built is needed. location.replace() keeps the view page out of the history.
(async function () {
  const guardKey = 'site-fixes:view-redirect:' + location.pathname;
  try {
    const last = Number(sessionStorage.getItem(guardKey) || 0);
    if (Date.now() - last < 10000) {
      // The image link came back to this page, e.g. the server redirected it again: stop instead of looping.
      return;
    }
  } catch (e) {
    // sessionStorage may be unavailable; the loop guard is then skipped.
  }

  const tokenLink = Array.from(document.querySelectorAll('a[href]')).find(
    (a) => a.origin === location.origin && a.pathname === location.pathname && /^\?[a-z0-9]+=[0-9a-f]+$/i.test(a.search)
  );
  if (!tokenLink) {
    return;
  }

  const response = await fetch(tokenLink.href, {credentials: 'include', referrer: location.href});
  const page = new DOMParser().parseFromString(await response.text(), 'text/html');
  // The image is shown as <img> on later visits; on the first visit there is only its download link (dl=1).
  const image = page.querySelector('img[src*=".fastpic.org/big/"]');
  const download = page.querySelector('a[href*=".fastpic.org/big/"]');
  const source = image ? image.getAttribute('src') : download && download.getAttribute('href');
  if (!source) {
    return;
  }

  const target = new URL(source, location.href);
  target.searchParams.delete('dl');
  try {
    sessionStorage.setItem(guardKey, String(Date.now()));
  } catch (e) {
    // See above.
  }
  location.replace(target.href);
})();
