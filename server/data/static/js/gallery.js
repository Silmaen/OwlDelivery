/**
 * Gallery lightbox: opens a screenshot in the native <dialog>, with previous / next.
 * Without JavaScript, every thumbnail is a plain link to its original image.
 */
document.addEventListener('DOMContentLoaded', function () {
  const dialog = document.getElementById('lightbox');
  const links = Array.from(document.querySelectorAll('[data-gallery-item]'));
  if (!dialog || !links.length || typeof dialog.showModal !== 'function') return;
  const image = dialog.querySelector('.lightbox__image');
  const caption = dialog.querySelector('.lightbox__caption');
  let current = 0;

  function show(index) {
    current = (index + links.length) % links.length;
    const link = links[current];
    image.src = link.href;
    image.alt = link.dataset.alt || '';
    caption.textContent = link.dataset.caption || '';
  }

  links.forEach(function (link, index) {
    link.addEventListener('click', function (event) {
      event.preventDefault();
      show(index);
      dialog.showModal();
    });
  });

  dialog.querySelector('[data-lightbox-prev]').addEventListener('click', function () { show(current - 1); });
  dialog.querySelector('[data-lightbox-next]').addEventListener('click', function () { show(current + 1); });
  dialog.querySelector('[data-lightbox-close]').addEventListener('click', function () { dialog.close(); });

  dialog.addEventListener('keydown', function (event) {
    if (event.key === 'ArrowLeft') show(current - 1);
    if (event.key === 'ArrowRight') show(current + 1);
  });
  // A click on the backdrop lands on the dialog itself.
  dialog.addEventListener('click', function (event) {
    if (event.target === dialog) dialog.close();
  });
  // Focus goes back to the thumbnail that was open.
  dialog.addEventListener('close', function () { links[current].focus(); });
});
