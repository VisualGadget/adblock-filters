// Fastpic popunder: on the first click it opens the clicked link in a new tab and sends the current tab to an ad,
// so Back walks through ad pages. Its script is blocked by rules/fastpic.json; this keeps it off when the code is
// served from another address or inline. The script installs itself as window.fpPop and calls it, so a read-only
// no-op in its place disables it.
Object.defineProperty(window, 'fpPop', {
  value: function () {},
  writable: false,
  configurable: false
});
