import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def safe_mode(series, default="-"):
    series = series.dropna()
    if series.empty:
        return default
    return series.mode().iloc[0]


def analyze_one_file(csv_path: Path, total_packets: int):
    df = pd.read_csv(csv_path)

    required_columns = [
        "topology",
        "distance_m",
        "payload_bytes",
        "seq",
        "sent_us",
        "recv_us",
        "latency_ms",
    ]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Kolom '{col}' tidak ditemukan di {csv_path}")

    # Konversi numerik
    df["distance_m"] = pd.to_numeric(df["distance_m"], errors="coerce")
    df["payload_bytes"] = pd.to_numeric(df["payload_bytes"], errors="coerce")
    df["seq"] = pd.to_numeric(df["seq"], errors="coerce")
    df["sent_us"] = pd.to_numeric(df["sent_us"], errors="coerce")
    df["recv_us"] = pd.to_numeric(df["recv_us"], errors="coerce")
    df["latency_ms"] = pd.to_numeric(df["latency_ms"], errors="coerce")

    # Hapus data rusak
    df = df.dropna(subset=[
        "payload_bytes",
        "seq",
        "sent_us",
        "recv_us",
        "latency_ms",
    ])

    # Sequence harus integer
    df["seq"] = df["seq"].astype(int)

    # Kalau ada duplikasi sequence, ambil data pertama
    df_unique = df.sort_values("seq").drop_duplicates(subset=["seq"], keep="first")

    received_packets = len(df_unique)
    lost_packets = max(total_packets - received_packets, 0)
    packet_loss_percent = (lost_packets / total_packets) * 100

    topology = safe_mode(df_unique["topology"])
    distance_m = safe_mode(df_unique["distance_m"])
    payload_bytes = int(safe_mode(df_unique["payload_bytes"], 0))

    if received_packets >= 2:
        duration_sec = (df_unique["recv_us"].max() - df_unique["recv_us"].min()) / 1_000_000
    else:
        duration_sec = 0

    if duration_sec > 0:
        throughput_bps = (received_packets * payload_bytes * 8) / duration_sec
    else:
        throughput_bps = 0

    throughput_kbps = throughput_bps / 1000

    latency_avg = df_unique["latency_ms"].mean() if received_packets > 0 else 0
    latency_min = df_unique["latency_ms"].min() if received_packets > 0 else 0
    latency_max = df_unique["latency_ms"].max() if received_packets > 0 else 0
    latency_std = df_unique["latency_ms"].std() if received_packets > 1 else 0

    received_seq = set(df_unique["seq"].tolist())
    expected_seq = set(range(total_packets))
    missing_seq = sorted(list(expected_seq - received_seq))

    return {
        "file": csv_path.name,
        "topology": topology,
        "distance_m": distance_m,
        "payload_bytes": payload_bytes,
        "total_packets": total_packets,
        "received_packets": received_packets,
        "lost_packets": lost_packets,
        "packet_loss_percent": round(packet_loss_percent, 3),
        "duration_sec": round(duration_sec, 3),
        "latency_avg_ms": round(latency_avg, 3),
        "latency_min_ms": round(latency_min, 3),
        "latency_max_ms": round(latency_max, 3),
        "latency_std_ms": round(latency_std, 3),
        "throughput_bps": round(throughput_bps, 3),
        "throughput_kbps": round(throughput_kbps, 3),
        "missing_seq": " ".join(map(str, missing_seq[:50])),
        "missing_seq_count": len(missing_seq),
    }


def get_input_files(input_path: Path):
    if input_path.is_file():
        return [input_path]

    if input_path.is_dir():
        return sorted(input_path.glob("*.csv"))

    raise FileNotFoundError(f"Input tidak ditemukan: {input_path}")


def create_plots(summary_df: pd.DataFrame, plot_dir: Path, input_path: Path):
    """
    Fungsi visualisasi dengan estetika tinggi. Identitas warna dikunci untuk tiap parameter QoS.
    """
    plot_dir.mkdir(parents=True, exist_ok=True)

    # --- PENGATURAN TEMA & WARNA KONSISTEN ---
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.4
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["axes.edgecolor"] = "#CCCCCC"
    
    # Identitas Warna QoS yang dikunci
    COLOR_LATENCY = "#E63946"     # Merah Crimson
    COLOR_LOSS = "#F4A261"        # Oranye Mustard
    COLOR_THROUGHPUT = "#2A9D8F"  # Hijau Teal

    # Label skenario
    summary_df["scenario"] = (
        summary_df["topology"].astype(str)
        + "_"
        + summary_df["distance_m"].astype(str)
        + "m_"
        + summary_df["payload_bytes"].astype(str)
        + "B"
    )

    # =========================================================================
    # 1. GRAFIK INDIVIDU (REAL-TIME PER FILE CSV)
    # =========================================================================
    for _, row in summary_df.iterrows():
        try:
            actual_file_path = input_path if input_path.is_file() else input_path / row["file"]
            
            if not actual_file_path.exists():
                continue
                
            df_raw = pd.read_csv(actual_file_path)
            df_raw = df_raw.dropna(subset=["payload_bytes", "seq", "sent_us", "recv_us", "latency_ms"])
            df_raw["seq"] = df_raw["seq"].astype(int)
            df_raw = df_raw.sort_values("seq").drop_duplicates(subset=["seq"], keep="first").reset_index(drop=True)

            if df_raw.empty:
                continue

            # Perhitungan Data Kumulatif
            df_raw["cum_packets"] = range(1, len(df_raw) + 1)
            df_raw["cum_loss_pct"] = ((df_raw["seq"] + 1 - df_raw["cum_packets"]) / (df_raw["seq"] + 1)) * 100
            df_raw["cum_loss_pct"] = df_raw["cum_loss_pct"].clip(lower=0)
            
            df_raw["duration_sec"] = (df_raw["recv_us"] - df_raw["recv_us"].iloc[0]) / 1_000_000
            df_raw["cum_bytes"] = df_raw["payload_bytes"].cumsum()
            df_raw["cum_throughput_kbps"] = (df_raw["cum_bytes"] * 8 / 1000) / df_raw["duration_sec"]
            df_raw["cum_throughput_kbps"] = df_raw["cum_throughput_kbps"].fillna(0).replace([float('inf'), float('-inf')], 0)

            fig_single, axes_single = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
            fig_single.suptitle(f"Distribusi 3 QoS: {row['file']}", fontsize=14, fontweight='bold', y=0.96)

            # A. Latency (Warna: Merah Crimson)
            axes_single[0].plot(df_raw["seq"], df_raw["latency_ms"], color=COLOR_LATENCY, linewidth=1.5)
            axes_single[0].fill_between(df_raw["seq"], df_raw["latency_ms"], color=COLOR_LATENCY, alpha=0.15)
            axes_single[0].set_ylabel("Latency (ms)", fontweight='bold', color=COLOR_LATENCY)
            axes_single[0].set_title("Fluktuasi Latency", loc='left', fontsize=11)

            # B. Packet Loss (Warna: Oranye Mustard)
            axes_single[1].plot(df_raw["seq"], df_raw["cum_loss_pct"], color=COLOR_LOSS, linewidth=2)
            axes_single[1].fill_between(df_raw["seq"], df_raw["cum_loss_pct"], color=COLOR_LOSS, alpha=0.15)
            axes_single[1].set_ylabel("Packet Loss (%)", fontweight='bold', color=COLOR_LOSS)
            axes_single[1].set_title("Kumulatif Packet Loss", loc='left', fontsize=11)
            axes_single[1].set_ylim(-5, max(10, df_raw["cum_loss_pct"].max() + 5))

            # C. Throughput (Warna: Hijau Teal)
            axes_single[2].plot(df_raw["seq"], df_raw["cum_throughput_kbps"], color=COLOR_THROUGHPUT, linewidth=2)
            axes_single[2].fill_between(df_raw["seq"], df_raw["cum_throughput_kbps"], color=COLOR_THROUGHPUT, alpha=0.15)
            axes_single[2].set_ylabel("Throughput (kbps)", fontweight='bold', color=COLOR_THROUGHPUT)
            axes_single[2].set_xlabel("Sequence Number (Paket)", fontweight='bold')
            axes_single[2].set_title("Stabilitas Throughput", loc='left', fontsize=11)

            plt.tight_layout(rect=[0, 0, 1, 0.95])
            
            single_img_name = plot_dir / f"single_qos_{Path(row['file']).stem}.png"
            plt.savefig(single_img_name, dpi=300)
            plt.close()

        except Exception as e:
            print(f"Gagal memproses grafik individu untuk {row['file']}: {e}")

    # =========================================================================
    # 2. GRAFIK GABUNGAN MAKRO (REKAP SELURUH SKENARIO)
    # =========================================================================
    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
    fig.suptitle("Komparasi 3 QoS Seluruh Skenario Pengujian", fontsize=16, fontweight='bold', y=0.96)

    x_labels = summary_df["scenario"]

    # A. Latency Rata-rata (Merah Crimson)
    axes[0].plot(x_labels, summary_df["latency_avg_ms"], marker="o", color=COLOR_LATENCY, linewidth=2.5, markersize=8)
    axes[0].fill_between(x_labels, summary_df["latency_avg_ms"], color=COLOR_LATENCY, alpha=0.1)
    axes[0].set_ylabel("Avg Latency (ms)", fontweight='bold', color=COLOR_LATENCY)
    axes[0].set_title("A. Rata-Rata Latency", loc='left', fontsize=12)
    # Tambahkan angka di atas titik marker
    for i, txt in enumerate(summary_df["latency_avg_ms"]):
        axes[0].annotate(f"{txt:.1f}", (i, summary_df["latency_avg_ms"].iloc[i]), 
                         textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color=COLOR_LATENCY)

    # B. Packet Loss (Oranye Mustard)
    axes[1].plot(x_labels, summary_df["packet_loss_percent"], marker="s", color=COLOR_LOSS, linewidth=2.5, markersize=8)
    axes[1].fill_between(x_labels, summary_df["packet_loss_percent"], color=COLOR_LOSS, alpha=0.1)
    axes[1].set_ylabel("Packet Loss (%)", fontweight='bold', color=COLOR_LOSS)
    axes[1].set_title("B. Total Packet Loss", loc='left', fontsize=12)
    axes[1].set_ylim(-5, max(15, summary_df["packet_loss_percent"].max() + 10))
    for i, txt in enumerate(summary_df["packet_loss_percent"]):
        axes[1].annotate(f"{txt:.1f}%", (i, summary_df["packet_loss_percent"].iloc[i]), 
                         textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color=COLOR_LOSS)

    # C. Throughput (Hijau Teal)
    axes[2].plot(x_labels, summary_df["throughput_kbps"], marker="^", color=COLOR_THROUGHPUT, linewidth=2.5, markersize=9)
    axes[2].fill_between(x_labels, summary_df["throughput_kbps"], color=COLOR_THROUGHPUT, alpha=0.1)
    axes[2].set_ylabel("Throughput (kbps)", fontweight='bold', color=COLOR_THROUGHPUT)
    axes[2].set_xlabel("Skenario Pengujian (Topologi_Jarak_Payload)", fontweight='bold', fontsize=12)
    axes[2].set_title("C. Kapasitas Throughput", loc='left', fontsize=12)
    for i, txt in enumerate(summary_df["throughput_kbps"]):
        axes[2].annotate(f"{txt:.1f}", (i, summary_df["throughput_kbps"].iloc[i]), 
                         textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color=COLOR_THROUGHPUT)

    plt.xticks(rotation=25, ha="right", fontsize=10)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    combined_img_name = plot_dir / "gabungan_summary_3_qos.png"
    plt.savefig(combined_img_name, dpi=300)
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="ESP32 Mesh QoS Analyzer"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="File CSV atau folder data CSV, contoh: data atau data/2x2_2_5m_32B.csv"
    )

    parser.add_argument(
        "--output",
        default="result/qos_summary.csv",
        help="File output rekap QoS. Default: result/qos_summary.csv"
    )

    parser.add_argument(
        "--total",
        type=int,
        default=500,
        help="Total paket dikirim per skenario. Default: 500"
    )

    parser.add_argument(
        "--plot",
        default=None,
        help="Folder output grafik. Contoh: result"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = get_input_files(input_path)

    if not files:
        print("Tidak ada file CSV yang ditemukan.")
        return

    summaries = []

    for csv_file in files:
        try:
            print(f"Menganalisis: {csv_file}")
            result = analyze_one_file(csv_file, args.total)
            summaries.append(result)
        except Exception as e:
            print(f"ERROR pada file {csv_file}: {e}")

    if not summaries:
        print("Tidak ada data yang berhasil dianalisis.")
        return

    summary_df = pd.DataFrame(summaries)

    summary_df = summary_df.sort_values(
        by=["topology", "distance_m", "payload_bytes"],
        ascending=True
    )

    summary_df.to_csv(output_path, index=False)

    print()
    print("=== HASIL REKAP QoS ===")
    print(summary_df[[
        "file",
        "topology",
        "distance_m",
        "payload_bytes",
        "received_packets",
        "packet_loss_percent",
        "latency_avg_ms",
        "throughput_kbps",
    ]])

    print()
    print(f"Rekap QoS tersimpan di: {output_path}")

    if args.plot:
        plot_dir = Path(args.plot)
        # Menambahkan input_path agar pembacaan re-draw data berjalan mulus
        create_plots(summary_df, plot_dir, input_path)
        print(f"Grafik tersimpan di folder: {plot_dir}")


if __name__ == "__main__":
    main()