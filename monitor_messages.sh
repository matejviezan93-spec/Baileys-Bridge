clear
#!/usr/bin/env bash
echo "📡 Symbióza WhatsApp Monitor"
echo "──────────────────────────────────────────────"
docker exec -i bridge_redis redis-cli PSUBSCRIBE ai_* | while read line; do
  ts=$(date '+%H:%M:%S')
  if [[ "$line" == *"ai_request"* ]]; then
    echo -e "\033[1;32m[$ts] 📥 INCOMING → $line\033[0m"
  elif [[ "$line" == *"ai_response"* ]]; then
    echo -e "\033[1;34m[$ts] 📤 OUTGOING → $line\033[0m"
  else
    echo "[$ts] $line"
  fi
done
