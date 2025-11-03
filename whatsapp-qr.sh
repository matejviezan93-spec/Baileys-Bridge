#!/usr/bin/env bash
# 🧬 Symbióza WhatsApp QR — zobrazí aktuální QR kód z bridge-worker logů

set -e
clear

# Kontrola závislostí
for cmd in qrencode docker; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "❌ Missing dependency: $cmd"
    echo "   → sudo apt install -y qrencode"
    exit 1
  fi
done

# Název kontejneru, který vypisuje QR
container="baileys-bridge-baileys_worker-1"
last_qr=""

# 🧩 Načti poslední QR z logů (aby něco bylo hned)
last_block=$(docker logs --tail=500 "$container" 2>&1 | awk '/WhatsApp QR/{getline; print}' | tail -n1)
if [ -n "$last_block" ]; then
  last_qr=$(echo "$last_block" | tr -d '\r\n' | xargs)
  clear
  echo "$last_qr" | qrencode -t ANSI -s 1 -m 1
fi

# 🧩 Sleduj nové QR v reálném čase
docker logs -f --since=1s "$container" 2>&1 | while IFS= read -r line; do
  if [[ "$line" =~ "WhatsApp QR" ]]; then
    read -r nextline || continue
    qr=$(echo "$nextline" | tr -d '\r\n' | xargs)

    if [ -z "$qr" ] || [ "$qr" = "$last_qr" ]; then
      continue
    fi

    last_qr="$qr"
    clear
    echo "📱 Naskenuj tento QR kód ve WhatsAppu (Linked Devices):"
    echo
    echo "$qr" | qrencode -t ANSI -s 1 -m 1
    echo
    echo "✅ Po přihlášení se session uloží do /data/session/auth_info.json"
  fi
done
