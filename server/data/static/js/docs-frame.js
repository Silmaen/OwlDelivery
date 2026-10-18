/**
 * Documentation frame: the address bar follows the page open in the doxygen frame, so a link can be shared,
 * and the tab title is the title of that page.
 */
document.addEventListener('DOMContentLoaded', function () {
  const frame = document.querySelector('[data-doc-frame]');
  if (!frame) return;
  const rawRoot = frame.dataset.rawRoot;
  const pageRoot = frame.dataset.pageRoot;
  const rawLink = document.querySelector('[data-doc-raw]');
  const siteTitle = document.title;

  // The anchor of a shared link never reaches the server: hand it to the frame.
  if (location.hash) frame.src = frame.getAttribute('src') + location.hash;

  frame.addEventListener('load', function () {
    let page;
    try {
      page = frame.contentWindow.location;
    } catch (error) {
      return; // A page of another site: nothing to follow.
    }
    if (!page.pathname.startsWith(rawRoot)) return;
    const relative = page.pathname.slice(rawRoot.length);
    const url = pageRoot + (relative === 'index.html' ? '' : relative) + page.search + page.hash;
    if (url !== location.pathname + location.search + location.hash) history.replaceState(null, '', url);
    if (rawLink) rawLink.href = page.href;
    const title = frame.contentDocument && frame.contentDocument.title;
    document.title = title ? title + ' — ' + siteTitle : siteTitle;
  });
});
