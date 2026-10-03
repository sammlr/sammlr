/* Display controls only. No network, storage, identity or trade commands. */
document.querySelector('[data-open-groups]')?.addEventListener('click', () => {
  document.querySelectorAll('.trade-group details').forEach(group => { group.open = true; });
});
document.querySelector('[data-close-groups]')?.addEventListener('click', () => {
  document.querySelectorAll('.trade-group details').forEach(group => { group.open = false; });
});

// Measure the first real canonical wall grid cell, never derive another card size.
// Fractional grid columns can differ by 1/64px; use the same first-column object
// consistently throughout this page, as the approved Trade reference does.
function syncCardWidth() {
  const cell = [...document.querySelectorAll('.wall > :first-child')]
    .find(element => element.getBoundingClientRect().width > 0);
  if (cell) document.documentElement.style.setProperty('--trade-card-width', `${cell.getBoundingClientRect().width}px`);
}
syncCardWidth();
new ResizeObserver(syncCardWidth).observe(document.querySelector('main.container'));
