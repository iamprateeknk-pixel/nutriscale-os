#!/bin/bash
# Serveo HTTPS tunnel — the Box reaches the internet only via a local proxy (127.0.0.1:3128), so SSH goes through it.
# (A Cloudflare quick tunnel does not work here: its client ignores the proxy and there is no direct route.)
# Reconnects within 10 s if it drops; each link is written to PUBLIC_URL.txt — the link CHANGES on every reconnect.
cd "$(dirname "$0")/../.."
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519
PROXY="${TUNNEL_PROXY:-127.0.0.1:3128}"
while true; do
  ssh -T -i ~/.ssh/id_ed25519 -o ProxyCommand="nc -X connect -x $PROXY %h %p" \
      -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
      -R 80:127.0.0.1:8765 serveo.net 2>&1 | while IFS= read -r line; do
        echo "$(date -Is) $line" >> logs/tunnel.log
        # Only the 'Forwarding' line — Serveo's tip/console links (console.serveo.net) are not the tunnel link
        u=$(echo "$line" | grep 'Forwarding' | grep -o 'https://[a-z0-9.-]*' | head -1)
        [ -n "$u" ] && echo "$u" > PUBLIC_URL.txt
      done
  echo "$(date -Is) tunnel dropped — reconnecting in 10 s" >> logs/tunnel.log; sleep 10
done
