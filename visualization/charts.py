from pathlib import Path


def plot_execution_times(records, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels = [r["experiment"] for r in records]
    times = [r["execution_time_seconds"] for r in records]
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots()
    ax.bar(labels, times)
    ax.set_ylabel("Waktu eksekusi (detik)")
    ax.set_title("Perbandingan waktu pemrosesan")
    fig.tight_layout()
    fig.savefig(target, dpi=150)
    plt.close(fig)
    return str(target)
