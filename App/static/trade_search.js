// View-only GET filters. No persistence, requests or inventory writes.
const form = document.querySelector('.sap-filters');
if (form) {
    for (const button of form.querySelectorAll('[data-albums]')) {
        button.hidden = false;
        button.addEventListener('click', () => {
            for (const input of form.querySelectorAll('[name="album"]')) {
                input.checked = button.dataset.albums === 'all';
            }
            form.requestSubmit();
        });
    }
    for (const input of form.querySelectorAll('[name="album"]')) {
        input.addEventListener('change', () => form.requestSubmit());
    }
}
