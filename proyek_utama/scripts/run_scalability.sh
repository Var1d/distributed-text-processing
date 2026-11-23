#!/usr/bin/env bash
# Jalankan di NODE MASTER. Menjalankan master untuk tiap jumlah worker, lalu menyalakan worker via SSH.
# Prasyarat: SSH tanpa password ke tiap worker, folder proyek sama di semua node, dataset ada di Master.
# Pakai:  MASTER_IP=192.168.1.10 bash scripts/run_scalability.sh scripts/workers.txt [dynamic|static]
# workers.txt: satu host per baris (9 baris). Host bernama "local" = jalankan worker di mesin ini (uji coba).
set -euo pipefail
HOSTS_FILE=${1:?isi: file daftar worker}; BAL=${2:-dynamic}
[[ -r "$HOSTS_FILE" ]] || { echo "Daftar worker tidak bisa dibaca: $HOSTS_FILE" >&2; exit 2; }
[[ "$BAL" == dynamic || "$BAL" == static ]] || { echo "Balancing harus dynamic atau static" >&2; exit 2; }
MASTER_IP=${MASTER_IP:-}; MASTER_BIND=${MASTER_BIND:-0.0.0.0}; PORT=${PORT:-5000}; DIR=${DIR:-$(pwd)}
CHUNK=${CHUNK:-10}; DATA=${DATA:-data/corpus}; REPEAT=${REPEAT:-3}; COUNTS=${COUNTS:-"1 2 4 6 9"}
[[ "$PORT" =~ ^[0-9]+$ ]] && ((PORT >= 1 && PORT <= 65535)) || { echo "PORT harus 1..65535" >&2; exit 2; }
mapfile -t HOSTS < <(grep -Ev '^[[:space:]]*(#|$)' "$HOSTS_FILE")
((${#HOSTS[@]} > 0)) || { echo "Daftar worker kosong" >&2; exit 2; }
if [[ -z "$MASTER_IP" ]]; then
  for h in "${HOSTS[@]}"; do
    [[ "$h" == local ]] || { echo "Set MASTER_IP ke alamat private master untuk worker SSH" >&2; exit 2; }
  done
  MASTER_IP=127.0.0.1
fi
[[ "$REPEAT" =~ ^[1-9][0-9]*$ && "$CHUNK" =~ ^[1-9][0-9]*$ ]] || { echo "REPEAT dan CHUNK harus bilangan positif" >&2; exit 2; }
mkdir -p results
ACTIVE_PIDS=()
cleanup() { for pid in "${ACTIVE_PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM
for n in $COUNTS; do
  [[ "$n" =~ ^[1-9][0-9]*$ ]] || { echo "Jumlah worker tidak valid: $n" >&2; exit 2; }
  (( n <= ${#HOSTS[@]} )) || { echo "Diminta $n worker, hanya ${#HOSTS[@]} host tersedia" >&2; exit 2; }
  for r in $(seq 1 "$REPEAT"); do
    label="dist_${BAL}_${n}w_r${r}"
    echo "=== $label ==="
    python3 master.py --data "$DATA" --host "$MASTER_BIND" --chunk "$CHUNK" --min-workers "$n" --port "$PORT" --startup-timeout 120 \
        --balancing "$BAL" --label "$label" > "results/$label.log" 2>&1 &
    MPID=$!; ACTIVE_PIDS+=("$MPID"); sleep 1
    for h in "${HOSTS[@]:0:$n}"; do
      if [ "$h" = "local" ]; then
        python3 worker.py --master "$MASTER_IP" --port "$PORT" > /dev/null 2>&1 &
      else
        REMOTE_DIR=$(printf '%q' "$DIR")
        REMOTE_MASTER=$(printf '%q' "$MASTER_IP")
        REMOTE_PORT=$(printf '%q' "$PORT")
        ssh -o BatchMode=yes "$h" "cd $REMOTE_DIR && python3 worker.py --master $REMOTE_MASTER --port $REMOTE_PORT" > /dev/null 2>&1 &
      fi
      ACTIVE_PIDS+=("$!")
    done
    wait "$MPID"; sleep 3
    for pid in "${ACTIVE_PIDS[@]}"; do wait "$pid" || true; done
    ACTIVE_PIDS=()
  done
done
echo "Selesai. Lihat results/summary.csv  (python analyze.py)"
