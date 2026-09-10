# Handoff package → copy into `deye-mqtt-dashboard-lcd-35`

Copy this entire folder into the new repo root (or as `docs/handoff/`).

Also copy these **source-of-truth** files into `reference/`:

| From (this repo) | To (new repo) |
|------------------|---------------|
| `homeassistant/iriv_deye_mqtt.yaml` | `reference/iriv_deye_mqtt.yaml` |
| `iriv/iriv-ioc-config.json` | `reference/iriv-ioc-config.json` |

Then tell Cursor: *Read `docs/handoff/HANDOFF.md` and `docs/handoff/mqtt-topics.md` before writing firmware.*

## Files in this package

| File | Purpose |
|------|---------|
| [HANDOFF.md](HANDOFF.md) | Architecture, hardware, stack decisions, constraints |
| [KEYWORDS.md](KEYWORDS.md) | Searchable domain keywords for agents / RAG |
| [mqtt-topics.md](mqtt-topics.md) | Full MQTT topic contract (subscribe map) |
