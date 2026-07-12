import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

import serial


EXPECTED_COLUMNS = [
    "topology",
    "distance_m",
    "payload_bytes",
    "from_node",
    "source_label",
    "seq",
    "sent_us",
    "recv_us",
    "latency_ms",
    "msg_length",
]


def parse_serial_line(line: str):
    """
    Menerima line dari Serial ESP32 root.
    Mengabaikan debug line yang diawali #.
    Mengambil hanya data CSV utama.
    """
    line = line.strip()

    if not line:
        return None

    if line.startswith("#"):
        return None

    if line.startswith("topology,distance_m"):
        return None

    parts = line.split(",")

    if len(parts) != len(EXPECTED_COLUMNS):
        return None

    return dict(zip(EXPECTED_COLUMNS, parts))


def main():
    parser = argparse.ArgumentParser(
        description="ESP32 Mesh Serial Logger to CSV"
    )

    parser.add_argument(
        "--port",
        required=True,
        help="Port serial root node, contoh: COM9"
    )

    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Baud rate serial. Default: 115200"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Nama file CSV output, contoh: data/2x2_2_5m_32B.csv"
    )

    parser.add_argument(
        "--expected",
        type=int,
        default=500,
        help="Jumlah paket yang diharapkan. Default: 500"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Batas waktu logging dalam detik. Default: 900 detik"
    )

    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["pc_timestamp"] + EXPECTED_COLUMNS

    print("=== ESP32 MESH SERIAL LOGGER ===")
    print(f"Port      : {args.port}")
    print(f"Baud      : {args.baud}")
    print(f"Output    : {output_path}")
    print(f"Expected  : {args.expected} paket")
    print(f"Timeout   : {args.timeout} detik")
    print()
    print("Pastikan Serial Monitor Arduino IDE sudah ditutup.")
    print("Mulai membaca serial...")
    print()

    received_unique_seq = set()
    total_rows_saved = 0
    start_time = time.time()

    try:
        with serial.Serial(args.port, args.baud, timeout=1) as ser, open(
            output_path, "w", newline="", encoding="utf-8"
        ) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Tunggu sebentar agar serial stabil
            time.sleep(2)

            while True:
                elapsed = time.time() - start_time

                if elapsed > args.timeout:
                    print("Logging berhenti karena timeout.")
                    break

                raw = ser.readline()

                if not raw:
                    continue

                try:
                    line = raw.decode("utf-8", errors="ignore").strip()
                except Exception:
                    continue

                # Tampilkan semua output untuk monitoring
                print(line)

                data = parse_serial_line(line)

                if data is None:
                    continue

                pc_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                row = {
                    "pc_timestamp": pc_timestamp,
                    **data,
                }

                writer.writerow(row)
                csvfile.flush()

                total_rows_saved += 1

                try:
                    seq = int(data["seq"])
                    received_unique_seq.add(seq)
                except ValueError:
                    pass

                if len(received_unique_seq) >= args.expected:
                    print()
                    print(f"Target {args.expected} paket unik tercapai.")
                    break

    except serial.SerialException as e:
        print()
        print("ERROR SERIAL:")
        print(e)
        print()
        print("Kemungkinan penyebab:")
        print("1. Port COM salah.")
        print("2. Serial Monitor Arduino IDE masih terbuka.")
        print("3. ESP32 root belum terhubung ke laptop.")
        return

    except KeyboardInterrupt:
        print()
        print("Logging dihentikan manual dengan Ctrl+C.")

    print()
    print("=== SELESAI ===")
    print(f"File CSV tersimpan : {output_path}")
    print(f"Total baris data   : {total_rows_saved}")
    print(f"Paket unik diterima: {len(received_unique_seq)}")


if __name__ == "__main__":
    main()