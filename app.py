from flask import Flask, render_template, Response, jsonify, request
import cv2
from ultralytics import YOLO
import time
import serial
import threading
import os
from datetime import datetime

app = Flask(__name__)
arduino = serial.Serial('/dev/ttyUSB0', 9600)
time.sleep(2)

# === GLOBAL ===
deteksi_kutu = {
    "kamera1": 0,
    "kamera2": 0
}
sensor_data = {
    "suhu_ruang": "---",
    "kelembaban": "---",
    "suhu_air": "---",
    "ppm": "---"
}
status_lampu = {"status": 0}  # 0 = OFF, 1 = ON

model = YOLO("model.pt")

cap1 = cv2.VideoCapture(0)
cap2 = cv2.VideoCapture(1)

# Periksa apakah kamera berhasil dibuka
if not cap1.isOpened():
    print("[Camera] Kamera 1 (index 0) tidak tersedia")
    cap1 = None
else:
    print("[Camera] Kamera 1 aktif")

if not cap2.isOpened():
    print("[Camera] Kamera 2 (index 1) tidak tersedia")
    cap2 = None
else:
    print("[Camera] Kamera 2 aktif")

threshold = 0.7

# === DETEKSI (TANPA KIRIM SERIAL) ===
def detect_and_send(frame, cam_id):
    results = model.predict(frame, stream=True, conf=0.65, iou=0.4, max_det=10)
    detected = False

    for result in results:
        boxes = result.boxes.xyxy
        probs = result.boxes.conf
        for i, box in enumerate(boxes):
            if probs[i] > threshold:
                detected = True
                x1, y1, x2, y2 = map(int, box)
                color = (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    # Simpan snapshot jika ada deteksi
    if detected:
        save_snapshot(frame, cam_id)

    # Update status deteksi
    if cam_id == 1:
        deteksi_kutu["kamera1"] = 1 if detected else 0
    elif cam_id == 2:
        deteksi_kutu["kamera2"] = 1 if detected else 0

    return frame

# === THREAD: Loop Kamera ===
def kamera_loop(cap, cam_id):
    while cap is not None and cap.isOpened():
        success, frame = cap.read()
        if success:
            frame = cv2.resize(frame, (960, 720))
            detect_and_send(frame, cam_id)
        time.sleep(0.1)  # batasi beban CPU

SNAPSHOT_DIR = os.path.join('static', 'snapshots')
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
for minggu in range(1, 5):
    for kamera in ['kamera1', 'kamera2']:
        os.makedirs(os.path.join(SNAPSHOT_DIR, f'minggu{minggu}', kamera), exist_ok=True)

def save_snapshot(frame, cam_id):
    now = datetime.now()
    minggu = min(((now.day - 1) // 7) + 1, 4)
    folder = os.path.join(SNAPSHOT_DIR, f'minggu{minggu}', f'kamera{cam_id}')
    filename = f"cam{cam_id}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
    cv2.imwrite(os.path.join(folder, filename), frame)

def cleanup_snapshots():
    while True:
        now = datetime.now()
        if now.day == 1 and now.hour == 0:
            for i in range(1, 5):
                folder = os.path.join(SNAPSHOT_DIR, f'minggu{i}')
                for file in os.listdir(folder):
                    path = os.path.join(folder, file)
                    if os.path.isfile(path):
                        os.remove(path)
            print("[Cleanup] Snapshot dibersihkan karena awal bulan")
        time.sleep(3600)  # cek setiap jam

# === THREAD: Kontrol Relay (gabungan status kamera 1 dan 2) ===
def kontrol_relay():
    last_cmd = ""
    while True:
        k1 = deteksi_kutu["kamera1"]
        k2 = deteksi_kutu["kamera2"]

        # Tentukan perintah yang dikirim
        if k1 == 1 and k2 == 0:
            cmd = '1'  # hanya relay1 aktif
        elif k1 == 0 and k2 == 1:
            cmd = '2'  # hanya relay2 aktif
        elif k1 == 1 and k2 == 1:
            cmd = '3'  # dua relay aktif
        else:
            cmd = '0'  # semua relay mati

        if cmd != last_cmd:
            arduino.write(cmd.encode())
            print(f"[Relay] Kirim ke Arduino: {cmd}")
            last_cmd = cmd

        time.sleep(0.2)

# === STREAM KAMERA ===
def gen_frames(cam, cam_id):
    while True:
        if cam is None:
            break
        success, frame = cam.read()
        if not success:
            break
        frame = cv2.resize(frame, (960, 720))
        frame = detect_and_send(frame, cam_id)
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# === THREAD: Pembacaan Serial Sensor ===
def read_serial_data():
    global sensor_data
    while True:
        try:
            if arduino.in_waiting:
                line = arduino.readline().decode('utf-8').strip()
                if line.startswith("S:") and ",H:" in line and ",DS:" in line and ",PPM:" in line:
                    try:
                        suhu_ruang = line.split("S:")[1].split(",H:")[0]
                        kelembaban = line.split(",H:")[1].split(",DS:")[0]
                        suhu_air = line.split(",DS:")[1].split(",PPM:")[0]
                        ppm = line.split(",PPM:")[1]

                        # Langsung update ke UI, meskipun nan
                        sensor_data["suhu_ruang"] = suhu_ruang
                        sensor_data["kelembaban"] = kelembaban
                        sensor_data["suhu_air"] = suhu_air
                        sensor_data["ppm"] = ppm

                        print(f"[Sensor] DHT: {suhu_ruang}°C, H: {kelembaban}%, DS: {suhu_air}°C, PPM: {ppm}")
                    except Exception as e:
                        print(f"[ParseError] {e} | Line: {line}")
        except Exception as e:
            print(f"[SerialError] {e}")

# === THREAD: Loop Kamera ===
if cap1:
    threading.Thread(target=kamera_loop, args=(cap1, 1), daemon=True).start()
if cap2:
    threading.Thread(target=kamera_loop, args=(cap2, 2), daemon=True).start()

# === Jalankan Thread ===
threading.Thread(target=read_serial_data, daemon=True).start()
threading.Thread(target=kontrol_relay, daemon=True).start()
threading.Thread(target=cleanup_snapshots, daemon=True).start()

# === ROUTES ===
@app.route('/video1')
def video1():
    if cap1 is not None:
        return Response(gen_frames(cap1, 1), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return "Kamera 1 tidak tersedia", 503

@app.route('/video2')
def video2():
    if cap2 is not None:
        return Response(gen_frames(cap2, 2), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return "Kamera 2 tidak tersedia", 503

@app.route('/')
def index():
    query = request.args.get('query')
    return render_template('index.html', query=query)

@app.route('/kontrol')
def kontrol():
    query = request.args.get('query')
    return render_template('kontrol.html', query=query)

@app.route('/riwayat')
def riwayat():
    query = request.args.get('query', '').lower()
    snapshot_base = os.path.join('static', 'snapshots')
    data = {}
    for minggu in range(1, 5):
        minggu_key = f'minggu{minggu}'
        data[minggu_key] = {
            'kamera1': [],
            'kamera2': []
        }
        for kamera in ['kamera1', 'kamera2']:
            folder = os.path.join(snapshot_base, minggu_key, kamera)
            if os.path.exists(folder):
                data[minggu_key][kamera] = sorted(os.listdir(folder))
    return render_template('riwayat.html', snapshots=data, query=query)

@app.route('/profile')
def profile():
    query = request.args.get('query')
    return render_template('user-profile.html', query=query)

@app.route('/sensor_data')
def get_sensor_data():
    return jsonify(sensor_data)

@app.route('/status_deteksi_kutu')
def status_deteksi_kutu():
    return jsonify(deteksi_kutu)

@app.route('/lampu/status')
def lampu_status():
    return jsonify(status_lampu)

@app.route('/lampu/on', methods=['POST'])
def lampu_on():
    arduino.write(b'L1')
    status_lampu["status"] = 1
    print("[Lampu] Relay dinyalakan")
    return jsonify({"status": "on"})

@app.route('/lampu/off', methods=['POST'])
def lampu_off():
    arduino.write(b'L0')
    status_lampu["status"] = 0
    print("[Lampu] Relay dimatikan")
    return jsonify({"status": "off"})

# === JALANKAN APP ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
