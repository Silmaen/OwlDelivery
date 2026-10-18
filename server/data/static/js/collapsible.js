/**
 * Collapsible text: a block taller than its limit is folded to that height, with a button to unfold it.
 * Short blocks, and every block without JavaScript, stay fully shown.
 */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-collapsible]').forEach(function (block) {
    const content = block.querySelector('.collapsible__content');
    if (!content) return;
    block.classList.add('is-collapsed');
    // Folding only pays when it hides a good part of the text.
    if (content.scrollHeight <= content.clientHeight * 1.3) {
      block.classList.remove('is-collapsed');
      return;
    }
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn--sm collapsible__toggle';
    button.setAttribute('aria-controls', content.id);
    button.setAttribute('aria-expanded', 'false');
    button.textContent = block.dataset.more || 'Show more';
    button.addEventListener('click', function () {
      const collapsed = block.classList.toggle('is-collapsed');
      button.setAttribute('aria-expanded', String(!collapsed));
      button.textContent = collapsed ? (block.dataset.more || 'Show more') : (block.dataset.less || 'Show less');
      if (collapsed) block.scrollIntoView({ block: 'nearest' });
    });
    block.appendChild(button);
  });
});
