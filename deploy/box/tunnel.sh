#!/bin/bash
# Serveo HTTPS tunnel — Box ka internet sirf local proxy (127.0.0.1:3128) se jaata hai, isliye SSH usi proxy se.
# (Cloudflare quick tunnel yahan nahi chalta: uska client proxy nahi maanta aur seedha raasta band hai.)
# Toote to 10 sec me dobara judta hai; har baar ka link PUBLIC_URL.txt me — har judne par link BADALTA hai.
cd "$(dirname "$0")/../.."
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519
PROXY="${TUNNEL_PROXY:-127.0.0.1:3128}"
while true; do
  ssh -T -i ~/.ssh/id_ed25519 -o ProxyCommand="nc -X connect -x $PROXY %h %p" \
      -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
      -R 80:127.0.0.1:8765 serveo.net 2>&1 | while IFS= read -r line; do
        echo "$(date -Is) $line" >> logs/tunnel.log
        # Sirf 'Forwarding' wali line — Serveo ke tip/console links (console.serveo.net) link nahi hain
        u=$(echo "$line" | grep 'Forwarding' | grep -o 'https://[a-z0-9.-]*' | head -1)
        [ -n "$u" ] && echo "$u" > PUBLIC_URL.txt
      done
  echo "$(date -Is) tunnel toota — 10 sec me dobara" >> logs/tunnel.log; sleep 10
done
