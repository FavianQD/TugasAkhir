import argparse
from pathlib import Path

import pandas as pd
import numpy as np
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

    # Hapus data rusak struktural
    df = df.dropna(subset=[
        "payload_bytes",
        "seq",
        "sent_us",
        "recv_us",
        "latency_ms",
    ])

    # Sequence harus integer
    df["seq"] = df["seq"].astype(int)

    # Kalau ada duplikasi sequence, ambil data pertama (Indikator paket sampai)
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

    # --- PENYELAMATAN DATA LATENCY (Mengisolasi data >= 0 akibat unsynced clock ESP32) ---
    valid_latency_series = df_unique[df_unique["latency_ms"] >= 0]["latency_ms"]
    has_valid_latency = len(valid_latency_series) > 0

    latency_avg = valid_latency_series.mean() if has_valid_latency else 0
    latency_min = valid_latency_series.min() if has_valid_latency else 0
    latency_max = valid_latency_series.max() if has_valid_latency else 0
    latency_std = valid_latency_series.std() if len(valid_latency_series) > 1 else 0

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
    Fungsi visualisasi dengan estetika tinggi (Faceted Grouped Bar Charts).
    Mengunci identitas warna gradasi monokromatik untuk merepresentasikan beban payload.
    """
    plot_dir.mkdir(parents=True, exist_ok=True)

    # --- PENGATURAN TEMA AKADEMIK MINIMALIS & ELEGAN ---
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.3
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["axes.edgecolor"] = "#888888"
    plt.rcParams["axes.linewidth"] = 0.8
    
    # Palet Warna Korporat/Jurnal Internasional untuk Beban Payload
    # Light Sage Teal (128B), Muted Steel Blue (512B), Deep Navy (1024B)
    PALETTE = ["#A8DADC", "#457B9D", "#1D3557"] 
    COLOR_SINGLE_LINE = "#2A9D8F"

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

            # Amankan visualisasi real-time baris agar clock negatif di-clip ke nol
            df_raw["latency_ms"] = df_raw["latency_ms"].clip(lower=0)

            fig_single, axes_single = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
            fig_single.suptitle(f"Analisis Distribusi Skenario: {row['file']}", fontsize=13, fontweight='bold', y=0.97)

            metrics_single = ["latency_ms", "cum_loss_pct", "cum_throughput_kbps"]
            ylabels_single = ["Latency (ms)", "Packet Loss (%)", "Throughput (kbps)"]
            titles_single = ["Karakteristik Tunda (Latency)", "Akumulasi Kegagalan Paket (Packet Loss)", "Stabilitas Kapasitas (Throughput)"]

            for idx, (metric, ylabel, title_s) in enumerate(zip(metrics_single, ylabels_single, titles_single)):
                axes_single[idx].plot(df_raw["seq"], df_raw[metric], color=COLOR_SINGLE_LINE, linewidth=1.2, alpha=0.9)
                axes_single[idx].fill_between(df_raw["seq"], df_raw[metric], color=COLOR_SINGLE_LINE, alpha=0.08)
                axes_single[idx].set_ylabel(ylabel, fontsize=9, fontweight='bold')
                axes_single[idx].set_title(title_s, loc='left', fontsize=10, pad=5)
                axes_single[idx].spines['top'].set_visible(False)
                axes_single[idx].spines['right'].set_visible(False)

            axes_single[2].set_xlabel("Sequence Number (Paket)", fontsize=10, fontweight='bold')
            plt.tight_layout(rect=[0, 0, 1, 0.95])
            
            single_img_name = plot_dir / f"single_qos_{Path(row['file']).stem}.png"
            plt.savefig(single_img_name, dpi=300)
            plt.close()

        except Exception as e:
            print(f"Gagal memproses grafik individu untuk {row['file']}: {e}")

    # =========================================================================
    # 2. GRAFIK GABUNGAN MAKRO (4D MULTIVARIATE FACETED BAR CHART)
    # =========================================================================
    # Memisahkan visualisasi menjadi 3 file gambar terpisah agar fokus, rapi, dan presisi
    metrics_macro = ["latency_avg_ms", "throughput_kbps", "packet_loss_percent"]
    y_labels_macro = ["Rata-Rata Latency (ms)", "Kapasitas Throughput (kbps)", "Persentase Packet Loss (%)"]
    titles_macro = [
        "Analisis Komparatif Latency Pengujian ESP-MESH",
        "Analisis Komparatif Kapasitas Throughput Pengujian ESP-MESH",
        "Analisis Komparatif Persentase Packet Loss Pengujian ESP-MESH"
    ]
    formats_macro = ["{:.1f}", "{:.1f}", "{:.1f}%"]

    for metric, ylabel, title, fmt in zip(metrics_macro, y_labels_macro, titles_macro, formats_macro):
        # Membuat panel bersebelahan (1 Baris, 2 Kolom) -> Kiri: 2x2, Kanan: 3x3
        fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
        fig.suptitle(title, fontsize=14, fontweight='bold', y=0.98)

        topologies = ["2x2", "3x3"]
        
        for idx, topo in enumerate(topologies):
            ax = axes[idx]
            df_topo = summary_df[summary_df["topology"] == topo]
            
            if df_topo.empty:
                ax.text(0.5, 0.5, "Data Skenario Tidak Ditemukan", ha='center', va='center')
                continue
                
            # Transformasi Pivot Data (X: Jarak, Grouping Balok: Payload)
            pivoted = df_topo.pivot(index="distance_m", columns="payload_bytes", values=metric)
            
            # Mengisi nilai kosong/NaN dengan 0 untuk mencegah crash penentuan tick grafik otomatis
            pivoted = pivoted.fillna(0)
            
            # Plot Bar berkelompok secara otomatis
            pivoted.plot(kind="bar", ax=ax, color=PALETTE, edgecolor="#555555", linewidth=0.6, width=0.75)
            
            ax.set_title(f"Topologi Grid {topo}", fontsize=12, fontweight='bold', pad=10)
            ax.set_xlabel("Jarak Transmisi Antar-Node (Meter)", fontsize=10, fontweight='bold')
            
            if idx == 0:
                ax.set_ylabel(ylabel, fontsize=10, fontweight='bold')
                
            ax.set_xticklabels(ax.get_xticklabels(), rotation=0) # Memastikan angka jarak berdiri tegak lurus rapi
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            # Mengatur tampilan Legend (Hanya dimunculkan di panel kanan agar menghemat ruang)
            if idx == 1:
                ax.legend(title="Beban Payload", labels=["128 Byte", "512 Byte", "1024 Byte"], 
                          loc="upper left", frameon=True, facecolor="#FFFFFF", edgecolor="#CCCCCC")
            else:
                if ax.get_legend() is not None:
                    ax.get_legend().remove()

            # Menaruh Label Angka Nilai di atas setiap balok grafik secara dinamis
            for p in ax.patches:
                height = p.get_height()
                if height >= 0:
                    ax.annotate(fmt.format(height),
                                (p.get_x() + p.get_width() / 2., height),
                                ha='center', va='bottom',
                                xytext=(0, 3),
                                textcoords='offset points',
                                fontsize=8.5, fontweight='normal', color="#222222")

        plt.tight_layout(rect=[0, 0, 1, 0.94])
        
        # Menyimpan file gambar representatif makro berdasarkan parameternya masing-masing
        combined_img_name = plot_dir / f"analisis_makro_{metric}.png"
        plt.savefig(combined_img_name, dpi=300)
        plt.close()


def main():
    parser = argparse.ArgumentParser(description="ESP32 Mesh QoS Analyzer")

    parser.add_argument("--input", required=True, help="File CSV atau folder data CSV")
    parser.add_argument("--output", default="result/qos_summary.csv", help="File output rekap QoS")
    parser.add_argument("--total", type=int, default=500, help="Total paket dikirim per skenario")
    parser.add_argument("--plot", default=None, help="Folder output grafik")

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
    summary_df = summary_df.sort_values(by=["topology", "distance_m", "payload_bytes"], ascending=True)
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
        create_plots(summary_df, plot_dir, input_path)
        print(f"Grafik tersimpan di folder: {plot_dir}")


if __name__ == "__main__":
    main()