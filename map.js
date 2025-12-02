const map = L.map('map').setView([57.615, 18.28], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap'
}).addTo(map);

L.marker([57.615, 18.28])
  .addTo(map)
  .bindPopup('Visby Soltipp');
