/**
 * Accordion — toggle collapsible panels with aria-expanded.
 */
function toggleAccordion(id) {
  const wrapper = document.getElementById(id);
  if (!wrapper) return;
  const trigger = wrapper.querySelector('.accordion__trigger');
  const panel = wrapper.querySelector('.accordion__panel');
  if (!trigger || !panel) return;
  const expanded = trigger.getAttribute('aria-expanded') === 'true';
  trigger.setAttribute('aria-expanded', String(!expanded));
  panel.classList.toggle('is-open');
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.accordion__trigger').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const wrapper = btn.closest('.accordion');
      if (wrapper && wrapper.id) toggleAccordion(wrapper.id);
    });
  });
});
