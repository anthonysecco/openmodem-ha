# OpenModem for Home Assistant

A [HACS](https://hacs.xyz/) custom integration for [OpenModem](https://github.com/anthonysecco/OpenModem) — a local web front end for the Quectel RM520N-GL modem. This integration polls OpenModem's `ha_state.sh` endpoint over your LAN and exposes the modem's signal, registration, carrier aggregation, WAN, LAN, and connectivity-check data as Home Assistant entities.

No cloud, no API keys — this talks directly to the modem's own web server on your network, the same way OpenModem's own dashboard does.

**Requires OpenModem with `ha_state.sh`** (added after commit `4612e45`). If your OpenModem install predates that, update it first via the System page's Update button or `installer.sh` before setting this up.

## ⚠️ Not yet in the default HACS store

This integration isn't submitted to HACS's default repository list yet, so it has to be added as a **custom repository** for now (see below). That's a normal, fully-supported way to install with HACS — it just means it doesn't show up if you search HACS without adding it first.

## Installation

### Option A — HACS custom repository (recommended)

1. In Home Assistant, go to **HACS → Integrations**.
2. Click the **⋮** menu (top right) → **Custom repositories**.
3. Add:
   - **Repository**: `https://github.com/anthonysecco/openmodem-ha`
   - **Category**: `Integration`
4. Click **Add**, then find **OpenModem** in the HACS integration list and click **Download**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration**, search for **OpenModem**, and enter your modem's LAN IP address (e.g. `192.168.225.1`) and port (default `8080`).

### Option B — Manual install

1. Copy `custom_components/openmodem` from this repo into your Home Assistant config directory, so you end up with `<config>/custom_components/openmodem/`.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**, search for **OpenModem**, and enter your modem's LAN IP address and port.

## Configuration

Set up entirely through the UI (config flow) — no YAML.

| Field | Default | Notes |
|---|---|---|
| Host | — | Your modem's LAN IP, e.g. `192.168.225.1` |
| Port | `8080` | OpenModem's web UI port |
| Scan interval | `10` seconds | How often *this integration* re-reads `ha_state.sh`. `ha_state.sh` itself does no polling of its own — it just reflects whatever OpenModem's own pollers last wrote — so this doesn't add extra load on the modem or AT bus; it only controls how fresh Home Assistant's copy is. |

## What's included

All entities group under a single **OpenModem** device. Most are `diagnostic`-category and a few sensitive ones (IMEI, IMSI, ICCID, phone number) are disabled by default — enable them individually in **Settings → Devices & Services → OpenModem → Entities** if you want them.

- **Device**: model, IMEI, firmware, temperature, uptime
- **SIM**: status, IMSI, ICCID, active slot, phone number
- **Registration**: LTE/5G NR/circuit-switched registration state
- **Signal**: LTE + 5G NR RSRP/RSRQ/SINR
- **Serving cell**: LTE and 5G NR connection state, cell ID, PCID, band, EARFCN/ARFCN, TAC (as both `binary_sensor`s for "connected" and detail `sensor`s)
- **Carrier**: name, PLMN, access technology
- **Carrier aggregation**: active carrier count (with full per-carrier detail — band, bandwidth, PCI, RSRP/RSRQ/SINR, MIMO layers, estimated/max Mbps — as attributes), aggregate bandwidth, estimated/maximum downlink throughput
- **Network/band preference**: preferred RAT mode, LTE/NR5G band locks, data roaming (all **read-only** — see below)
- **WAN**: APN, IPv4/IPv6, active state, cumulative data sent/received, and **live send/receive rate** (computed server-side by `ha_state.sh` from the byte-counter delta between polls)
- **LAN**: router IP, DHCP range, NAT/passthrough mode, DNS mode
- **Connectivity**: ICMP reachability + latency/jitter, HTTP 204 connectivity-check reachability, Cloudflare edge PoP, WAN egress city/region/country
- **Last polled** timestamps for both the modem and connectivity pollers (disabled by default — mainly useful for diagnosing staleness)

## What's not included, and why

- **`_poll_duration_s` / `_poll_interval_s`** — internal poller bookkeeping (how long a cycle took, the configured interval), not modem telemetry. Not exposed as entities.
- **Everything is read-only.** OpenModem's `ha_state.sh` only *reads* state — there's no companion "set" endpoint wired in yet for things like band locking or network-mode preference (OpenModem's `band_lock.sh` has a `set` action, but it isn't part of this integration's data source). `net_mode_pref`, `net_data_roaming`, `band_pref_lte`, and `band_pref_nr5g` are exposed as read-only diagnostic sensors, not `select`/`switch` controls.
- **`reg_lte` / `reg_nr` / `reg_creg` / `carrier_act`** are plain string sensors, not Home Assistant's `enum` device class. `ha_state.sh` translates their raw AT status codes to strings (e.g. `"home"`, `"roaming"`, `"eutran"`), but falls back to `"code_N"` for anything outside its known table — and `enum` requires a fixed, closed set of options declared up front, which an open-ended fallback doesn't fit. Plain strings avoid that mismatch.
- **`internet_info.sh`, `band_lock.sh?action=get`, and the 5-minute history endpoints** aren't polled by this integration at all — by design, for now. The first two are on-demand endpoints outside OpenModem's normal poll cycle (one calls out to ipinfo.io fresh each time, the other issues a live AT command), and the history endpoints are rolling sample arrays better left to Home Assistant's own recorder/statistics once the point-in-time sensors above are being polled.

## Troubleshooting

- **"Could not connect"** during setup: confirm you can reach `http://<modem-ip>:8080/cgi-bin/ha_state.sh` directly from a browser on the same network as Home Assistant, and that OpenModem's firewall rules (`apply_iptables.sh`) allow that source interface — by default, port 8080 is only accepted from specific interfaces (LAN bridge, ethernet, Tailscale), not arbitrary sources.
- **"Unexpected response"**: your OpenModem install predates `ha_state.sh` — update it first.

## License

MIT — see [LICENSE](LICENSE).
