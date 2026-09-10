# Deye MQTT web dashboard

Static page that subscribes to the same `iriv/ivt/#` topics as the LCD. The browser talks **MQTT over WebSockets** — not TCP port 1883.

## Run locally

From this `web/` folder:

```powershell
python -m http.server 8080
```

Open `http://127.0.0.1:8080`. Gear icon → set the broker WebSocket URL (default `ws://<this-host>:9001`) → Connect.

Layouts (top-right toggle, remembered in the browser):

- **Simplify** — same tabs as the LCD. PV1 / PV2 stretch to full width.
- **Full** — KPI row, Deye-style flow graph, today energy, and live tables with data age. Battery **negative = charging**, **positive = discharging**. Grid CT matches HA/Deye Cloud: **positive = Import** (buy from grid), **negative = Export**. Load current is MQTT-only (not estimated from U×I).
- **Minimal** — old-school utility SCADA single-line diagram: black board, cyan/red orthogonal feeders, monospace tags, live MW strip.

Host the folder with nginx, Caddy, or GitHub Pages the same way. No backend is required.

## Enable WebSockets on Mosquitto (Pi)

MQTT 1883 is what IRIV and the LCD already use. Add a **second listener** for the browser:

```conf
# /etc/mosquitto/conf.d/websockets.conf
listener 9001
protocol websockets
allow_anonymous true
```

If the broker already uses a password file, keep that and drop `allow_anonymous`. Then:

```bash
sudo systemctl restart mosquitto
```

Open `9001/tcp` only on the LAN (or Tailscale), not on the public internet.

Optional nginx reverse proxy (TLS + same origin):

```nginx
location / {
    root /var/www/deye-dashboard;
    index index.html;
}

location /mqtt {
    proxy_pass http://127.0.0.1:9001/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

Then the page URL is `wss://your-host/mqtt` (set that in the gear dialog).

## Remote access

Do **not** port-forward 1883/9001 to the internet without TLS and auth.

Safer options:

1. **Tailscale / WireGuard** — open the dashboard and `ws://100.x.x.x:9001` on the tailnet.
2. **HTTPS reverse proxy** as above, with basic auth or VPN in front.

GitHub Pages can serve this folder, but the **broker** must still be reachable from the phone/PC (Pages cannot tunnel MQTT).

## Generic MQTT web clients

If you only need raw topics, skip this UI:

| Client | Notes |
|--------|--------|
| [HiveMQ Web Client](https://www.hivemq.com/demos/websocket-client/) | Browser; needs a public or LAN WebSocket listener |
| [MQTTX](https://mqttx.app/) | Desktop + web; TCP or WebSocket |
| [MQTT Explorer](https://mqtt-explorer.com/) | Desktop; good for debugging `iriv/ivt/#` |

Subscribe to `iriv/ivt/#`. Payload is `{"value": <number>}`.
