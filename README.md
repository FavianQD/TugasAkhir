ANALISIS QUALITY OF SERVICE (QoS) ESP-MESH PADA TOPOLOGI GRID

Repository ini berisi kode program, data, dan proses analisis yang digunakan dalam penelitian Tugas Akhir mengenai pengujian Quality of Service (QoS) pada jaringan ESP-MESH berbasis ESP32.
Penelitian menganalisis performa jaringan berdasarkan variasi topologi grid, jarak transmisi, dan ukuran payload. Parameter QoS yang digunakan adalah packet loss, throughput, dan latency.

CARA MENGGUNAKAN :
- RootNode: program ESP32 sebagai root/gateway. Terhubung ke laptop untuk mengirimkan data hasil pengujian melalui Serial.
- RouterNode: program ESP32 sebagai router/relay untuk meneruskan komunikasi mesh. Tidak mengirim data pengujian.
- LeafNode: program ESP32 sebagai leaf/end device yang mengirim 500 paket data pengujian.
- serial_logger.py: membaca data Serial dari Root Node dan menyimpannya otomatis sebagai CSV.
- qos_analyzerV2.py: membaca CSV hasil pengujian dan menghitung Latency, Packet Loss, dan Throughput.

PERSIAPAN :
- Gunakan ESP32, misalnya ESP32-WROOM-32 atau ESP32 Dev Module.
- Install library Arduino:
  - Painless Mesh
  - ArduinoJson
  - TaskScheduler
  - Async TCP by ESP32Async
- Pilih Tools > Board > ESP32 Arduino > ESP32 Dev Module.
- Pilih Tools > Port sesuai ESP32 yang digunakan.

PEMBAGIAN NODE GRID 2×2 :
- Posisi (0,0): RootNode
- Posisi (0,1): RouterNode dengan label ROUTER_01
- Posisi (1,0): RouterNode dengan label ROUTER_10
- Posisi (1,1): LeafNode dengan label LEAF_11
Sesuaikan juga yang 3x3 nya.
Root Node tetap harus terhubung ke laptop.
Router dan Leaf dapat menggunakan adaptor atau power bank.

PENGATURAN PAYLOAD :
Pada LeafNode ubah:
#define PAYLOAD_SIZE 128
Nilai dapat diganti menjadi 128, 512, atau 1024 byte. 
Setelah mengubah payload, upload ulang LeafNode.

PENGATURAN TOPOLOGI DAN JARAK
Pada RootNode sesuaikan:
#define TOPOLOGY_NAME "2x2"
#define DISTANCE_M "5"
Nilai jarak disesuaikan dengan skenario pengujian, misalnya 1, 3, atau 5 meter. 
Setelah mengubah konfigurasi, upload ulang RootNode.

SKENARIO PENGUJIAN
- Topologi: 2×2 dan 3×3
- Jarak: 1 m, 3 m, dan 5 m
- Payload: 128 B, 512 B, dan 1024 B
- Setiap skenario: 500 paket
- Total: 18 skenario

URUTAN PENGUJIAN
- Upload RootNode, RouterNode, dan LeafNode sesuai peran.
- Pasang label dan letakkan node sesuai topologi serta jarak pengujian.
- Hubungkan Root Node ke laptop.
- Nyalakan seluruh node dan tunggu sekitar 20–30 detik agar mesh terbentuk.
- Jalankan serial_logger.py.
- Reset Leaf Node agar sequence dimulai dari awal.
- Tunggu hingga 500 paket selesai diterima.
- Data otomatis disimpan ke folder data.

PERSIAPAN PYTHON
Install library:
pip install pyserial pandas matplotlib
Jika pip tidak terbaca:
python -m pip install pyserial pandas matplotlib

SERIAL LOGGER
Tutup Serial Monitor Arduino IDE agar port tidak digunakan aplikasi lain.
Contoh Root Node menggunakan COM9:
python serial_logger.py --port COM9 --baud 115200 --output data/2x2_5m_128B.csv --expected 500
Nama file disesuaikan dengan topologi, jarak, dan payload yang sedang diuji.


ANALISIS QoS
Untuk menganalisis satu file:
python qos_analyzerV2.py --input data/2x2_5m_128B.csv --output result/qos_summary.csv --total 500 --plot result
Untuk menganalisis seluruh CSV dalam folder data:
python qos_analyzerV2.py --input data --output result/qos_summary.csv --total 500 --plot result

HASIL ANALISIS
- result/qos_summary.csv: rekap hasil QoS setiap skenario.
- result/grafik_latency.png: grafik latency.
- result/grafik_packet_loss.png: grafik packet loss.
- result/grafik_throughput.png: grafik throughput.

PARAMETER QoS
- Latency: rata-rata waktu tempuh paket dari Leaf Node sampai Root Node.
- Packet Loss: persentase paket yang tidak diterima dari total 500 paket.
- Throughput: jumlah payload yang berhasil diterima dalam satuan waktu.

CATATAN
- Jangan membuka Serial Monitor saat serial_logger.py berjalan.
- Jika muncul Access Denied, periksa apakah port COM sedang digunakan aplikasi lain.
- Jika CSV kosong, periksa koneksi Root Node dan data yang diterima.
- Jika paket kurang dari 500, data tersebut menunjukkan adanya paket yang tidak diterima.
- Reset Leaf Node saat mengulang pengujian agar sequence dimulai dari awal.
- Upload ulang LeafNode setiap mengganti payload.
- Upload ulang RootNode setiap mengganti konfigurasi topologi atau jarak.
- Router Node cukup dinyalakan dan ditempatkan sesuai posisi karena berfungsi sebagai relay komunikasi mesh.


Repository ini digunakan sebagai dokumentasi implementasi dan pengolahan data dari penelitian Tugas Akhir saya.
Author: Favian Qintara Daffa
