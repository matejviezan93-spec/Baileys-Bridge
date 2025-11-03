#!/usr/bin/env bash
# 🧬 Symbióza WhatsApp QR — minimal terminal mode (only QR output)

set -e
clear

for cmd in qrencode docker; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "❌ Missing dependency: $cmd"
    echo "   → sudo apt install -y qrencode"
    exit 1
  fi
done

container="baileys-bridge-api_server-1"
last_qr=""

# 🧩 načti poslední QR z logů (aby něco bylo hned)
last_block=$(docker logs --tail=500 "$container" 2>&1 | awk '/Scan this QR with WhatsApp/{getline;print}' | tail -n1)
if [ -n "$last_block" ]; then
  last_qr=$(echo "$last_block" | tr -d '\r\n' | xargs)
  clear
  echo "$last_qr" | qrencode -t ANSI -s 1 -m 1
fi

# 🧩 sleduj nové QR
docker logs -f --since=1s "$container" 2>&1 | while IFS= read -r line; do
  if [[ "$line" =~ "Scan this QR with WhatsApp" ]]; then
    read -r nextline || continue
    qr=$(echo "$nextline" | tr -d '\r\n' | xargs)

    if [ -z "$qr" ] || [ "$qr" = "$last_qr" ]; then
      continue
    fi
    last_qr="$qr"

    clear
    echo "$qr" | qrencode -t ANSI-s 1 -m 1
  fi
done
