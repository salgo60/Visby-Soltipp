
// Simple ticker logic
document.addEventListener('DOMContentLoaded', function () {
  const ticker = document.getElementById('ticker');
  if (!ticker) return;
  const counters = ticker.querySelectorAll('.ticker-number');
  let started = false;

  function animateTicker() {
    if (started) return;
    const pos = ticker.getBoundingClientRect().top;
    if (pos < window.innerHeight) {
      started = true;
      counters.forEach(el => {
        const target = parseFloat(el.dataset.target);
        const decimals = parseInt(el.dataset.decimals || 0);
        let count = 0;
        const step = target / 100;

        const interval = setInterval(() => {
          count += step;
          if (count >= target) {
            count = target;
            clearInterval(interval);
          }
          el.textContent = count.toFixed(decimals);
        }, 20);
      });
    }
  }
  window.addEventListener('scroll', animateTicker);
  animateTicker();
});
