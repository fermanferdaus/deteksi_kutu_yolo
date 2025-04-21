function updateElement(url, elementId, formatData) {
    const element = document.getElementById(elementId);
    element.classList.remove('loaded'); // Opsional efek loading (tambahkan CSS kalau mau)

    fetch(url)
        .then(response => response.json())
        .then(data => {
            element.innerHTML = formatData ? formatData(data) : data;
        })
        .finally(() => {
            element.classList.add('loaded');
        });
}

function formatSuhuRuang(data) {
    return `<h6>${data.suhu_ruang} <span class="text-danger small pt-1 fw-bold"> °C</span></h6>`;
}

function formatSuhuAir(data) {
    return `<h6>${data.suhu_air} <span class="text-danger small pt-1 fw-bold"> °C</span></h6>`;
}

function formatKelembaban(data) {
    return `<h6>${data.kelembaban} <span class="text-danger small pt-1 fw-bold"> %</span></h6>`;
}

function formatNutrisi(data) {
    return `<h6>${data.ppm} <span class="text-danger small pt-1 fw-bold"> ppm</span></h6>`;
}

function formatKutuKamera1(data) {
    const status = data.kamera1 == 1 ? "Terdeteksi" : "Tidak Terdeteksi";
    const color = data.kamera1 == 1 ? "text-danger" : "text-success";
    return `<h4 class="${color} fw-bold">${status}</h4>`;
}

function formatKutuKamera2(data) {
    const status = data.kamera2 == 1 ? "Terdeteksi" : "Tidak Terdeteksi";
    const color = data.kamera2 == 1 ? "text-danger" : "text-success";
    return `<h4 class="${color} fw-bold">${status}</h4>`;
}

// Jalankan update pertama kali dan setiap 5 detik
function updateSensor() {
    updateElement('/sensor_data', 'suhu-ruang', formatSuhuRuang);
    updateElement('/sensor_data', 'kelembaban', formatKelembaban);
    updateElement('/sensor_data', 'suhu-air', formatSuhuAir);
    updateElement('/sensor_data', 'nutrisi', formatNutrisi);
}

function updateStatus(){
    updateElement('/status_deteksi_kutu', 'kutu1', formatKutuKamera1);
    updateElement('/status_deteksi_kutu', 'kutu2', formatKutuKamera2);
}

// Fungsi untuk toggle status lampu
function toggleLampu() {
    const switchButton = document.getElementById('lampuSwitch');
    const lampuStatus = document.getElementById('lampuStatus');

    if (switchButton.checked) {
        lampuStatus.textContent = 'ON';
        fetch('/lampu/on', { method: 'POST' }); 
    } else {
        lampuStatus.textContent = 'OFF';
        fetch('/lampu/off', { method: 'POST' });
    }
}

updateSensor();
setInterval(updateSensor, 5000);

updateStatus();
setInterval(updateStatus, 1000);
