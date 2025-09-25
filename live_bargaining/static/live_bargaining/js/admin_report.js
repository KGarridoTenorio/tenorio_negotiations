document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('form').style.display = 'none';

  let links = document.getElementsByClassName('nav-link');
  Array.from(links).forEach((link) => {
    if (link.href.includes("/demo/")) {
      link.href = "";
    }
  });
});

function do_refresh() {
  window.location.reload();
}