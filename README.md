# Parcel Tracker for Home Assistant (Posten/Bring & PostNord)

A Home Assistant custom integration that tracks the parcels on your personal
Norwegian carrier account and exposes them as sensors — number of active
parcels, what's arriving today, and your next expected delivery. Two carriers
are supported today: **Posten / Bring** and **PostNord**. You can add one or
both.

The integration is built around a **provider abstraction**, so each carrier is
an isolated provider and more can be added without touching the Home Assistant
platform code.

> ⚠️ **Important — unofficial APIs.** Neither carrier offers a public API for
> listing all parcels on a personal account, so this integration talks to the
> same private backends their own apps use:
>
> - **Posten/Bring** — the app backend (`api.posten.no` / `id.posten.no`),
>   authenticated with the Posten app's OAuth client via Vipps/phone login.
> - **PostNord** — the web app backend (`app.postnord.no`), authenticated with
>   your web **session cookie** after a Vipps login.
>
> These can **break at any time** if the carriers change their apps/backends,
> and the integration is **not endorsed by or affiliated with** Posten/Bring or
> PostNord. Use at your own risk and review each carrier's terms of service. If
> you only want to track a **known tracking number** via a documented API, see
> "Alternatives" at the bottom.

---

## What it does

- Logs in to your Posten account with **Vipps or your phone number** (OAuth2 authorization-code flow).
- Fetches all **incoming** parcels associated with your account.
- Normalizes each carrier's status into a common model.
- Exposes aggregate sensors plus (optionally) one sensor per parcel.
- Fires Home Assistant events on parcel changes for use in automations.

### Status normalization

Provider statuses are mapped to a shared set, while the original value is kept
as `raw_status`:

| Normalized | Meaning |
|---|---|
| `unknown` | Status not known |
| `registered` | Shipment registered / pre-notified |
| `in_transit` | On its way |
| `out_for_delivery` | Out for delivery |
| `ready_for_pickup` | Collectable at a pickup point |
| `delivered` | Delivered |
| `delayed` | Delayed |
| `returned` | Returned to sender |

---

## Installation

### HACS (recommended)

1. In HACS → **Integrations** → three-dot menu → **Custom repositories**.
2. Add this repository's URL, category **Integration**.
3. Search for **Parcel Tracker** and install it.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/parcel_tracker/` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Setup

Go to **Settings → Devices & Services → Add Integration**, choose
**Parcel Tracker**, then pick the carrier you want to add (**Posten / Bring** or
**PostNord**). Add the integration again to set up the second carrier.

### Posten / Bring

1. The dialog shows a **login link**. Open it in a browser and log in with
   **Vipps** or your **phone number**.
2. After login your browser is redirected to an address starting with
   `posten://login?code=...`. This page will usually fail to open — **that is
   expected**. Copy the whole address (or just the `code=` value) from the
   address bar.
3. Paste it back into Home Assistant. The integration exchanges it for tokens
   and finishes setup. If the session later expires, Home Assistant prompts you
   to re-authenticate the same way.

### PostNord

PostNord's web app authenticates with a **session cookie**, so setup is a
copy-paste of that cookie:

1. Open <https://app.postnord.no> in a browser and log in with **Vipps**.
2. Open developer tools (**F12**) → **Network**, reload the page, click the
   `shipments` request, and under **Request headers** copy the entire value of
   the **`Cookie`** header.
3. Paste it into the PostNord setup dialog.

The cookie is stored in Home Assistant and sent with each request. When it
expires, Home Assistant prompts you to paste a fresh one (there is no automatic
token refresh like Posten). Your Vipps credentials are never seen by the
integration.

### Posten/Bring authentication requirements

- A personal Posten account is required; you log in with **Vipps** or your
  **phone number**.
- The integration stores an OAuth **refresh token** in Home Assistant and uses
  it to obtain short-lived access tokens. Your login credentials are never seen
  or stored by the integration.
- No Mybring business account or API key is needed (that is a separate,
  sender-oriented product).

---

## Available entities

| Entity | Description |
|---|---|
| `sensor.parcel_tracker_active_parcels` | Number of incoming (active) parcels |
| `sensor.parcel_tracker_arriving_today` | Parcels expected today |
| `sensor.parcel_tracker_next_delivery` | Date of the next expected delivery |

The **Active parcels** sensor exposes a `packages` attribute: a list of all
incoming parcels, each a dict with the fields below. This is convenient for a
single dashboard card that lists everything without extra add-ons.

If **individual package entities** are enabled (default), each **incoming**
parcel also gets its own `sensor.*` (named after the sender) whose state is the
normalized status and whose attributes carry the full detail:

`kollinummer` (parcel number), `sendingsnummer` (consignment number), `sender`,
`recipient`, `recipient_address`, `recipient_postal_code`, `recipient_city`,
`status`, `status_text`, `delivery_method` (Home delivery / Mailbox delivery /
Pickup point / …), `expected_delivery`, `delivery_window_start`,
`delivery_window_end`, `on_track`, `weight_kg`, `dimensions`, `transport`,
`carrier`, `tracking_url`, `latest_event`, `latest_event_time`, and `tracking`
(the full event history as a list of `{time, description, location}`).

Delivered/archived parcels do not get their own entity — only what's currently
incoming, so the dashboard stays clean.

> Exact entity IDs depend on your Home Assistant naming; the table shows the
> default slugs.

## Dashboard

You can list incoming parcels with a **Markdown card** (no custom cards needed),
driven by the `packages` attribute:

```yaml
type: markdown
title: 📦 Innkommende pakker
content: |
  {% set pkgs = state_attr('sensor.posten_bring_active_parcels', 'packages') or [] %}
  {% set methods = {'home_delivery':'Hjemlevering','mailbox_delivery':'Postkasse','pib_delivery':'Hentested','parcel_locker_delivery':'Pakkeboks','parcel_robot_delivery':'Leveringsrobot'} %}
  {% set statuses = {'registered':'Registrert','in_transit':'Underveis','out_for_delivery':'Ut for levering','ready_for_pickup':'Klar for henting','delivered':'Levert','delayed':'Forsinket','returned':'Returnert','unknown':'Ukjent'} %}
  {% set icons = {'in_transit':'🚚','out_for_delivery':'🚚','registered':'🕒','ready_for_pickup':'📍','delivered':'✅','delayed':'⚠️','returned':'↩️'} %}
  {% if pkgs %}
  | | Avsender | Levering | Forventet | Status |
  |:-:|:--|:--|:--|:--|
  {% for p in pkgs %}
  {%- set eta = '—' -%}
  {%- if p.expected_delivery -%}
    {%- if p.expected_delivery == now().strftime('%Y-%m-%d') -%}{%- set day = 'I dag' -%}
    {%- elif p.expected_delivery == (now()+timedelta(days=1)).strftime('%Y-%m-%d') -%}{%- set day = 'I morgen' -%}
    {%- else -%}{%- set day = as_timestamp(p.expected_delivery)|timestamp_custom('%d.%m.%Y', true) -%}{%- endif -%}
    {%- if p.delivery_window_start -%}{%- set eta = day ~ ' kl. ' ~ (as_timestamp(p.delivery_window_start)|timestamp_custom('%H:%M', true)) ~ '–' ~ (as_timestamp(p.delivery_window_end)|timestamp_custom('%H:%M', true)) -%}
    {%- else -%}{%- set eta = day -%}{%- endif -%}
  {%- endif -%}
  | {{ icons.get(p.status,'📦') }} | **{{ p.sender }}** | {{ methods.get(p.delivery_type, p.delivery_method) }} | {{ eta }} | {{ statuses.get(p.status, p.status) }} |
  {% endfor %}
  {% else %}
  _Ingen innkommende pakker akkurat nå._
  {% endif %}
```

> The entity_id depends on your integration's title — commonly
> `sensor.posten_bring_active_parcels`. Check **Developer Tools → States** and
> adjust the card if needed. For a richer, colourful UI, the
> [Mushroom](https://github.com/piitaya/lovelace-mushroom) cards (via HACS) pair
> nicely with the per-package entities.

### Parcel details

Each incoming parcel is its own entity (named after the sender), so clicking it
opens a dialog with every attribute. List them for one-click access with an
**Entities card** — or, dynamically, with the
[auto-entities](https://github.com/thomasloven/lovelace-auto-entities) card:

```yaml
type: custom:auto-entities
card:
  type: entities
  title: Pakker
filter:
  include:
    - integration: parcel_tracker
      attributes:
        kollinummer: "*"
```

For a fully formatted detail view (full tracking history, weight, size,
recipient) without any custom cards, use this **Markdown card**:

```yaml
type: markdown
title: 📦 Pakkedetaljer
content: |
  {% set pkgs = state_attr('sensor.posten_bring_active_parcels','packages') or [] %}
  {% set methods = {'home_delivery':'Hjemlevering','mailbox_delivery':'Postkasse','pib_delivery':'Hentested','parcel_locker_delivery':'Pakkeboks'} %}
  {% set statuses = {'registered':'Registrert','in_transit':'Underveis','ready_for_pickup':'Klar for henting','delivered':'Levert','delayed':'Forsinket'} %}
  {% if not pkgs %}_Ingen innkommende pakker._{% endif %}
  {% for p in pkgs %}
  ## 📦 {{ p.sender }} — {{ statuses.get(p.status, p.status) }}
  **Levering:** {{ methods.get(p.delivery_type, p.delivery_method) }}{% if p.expected_delivery %} · {% if p.expected_delivery == now().strftime('%Y-%m-%d') %}I dag{% else %}{{ as_timestamp(p.expected_delivery)|timestamp_custom('%d.%m.%Y', true) }}{% endif %}{% if p.delivery_window_start %} kl. {{ as_timestamp(p.delivery_window_start)|timestamp_custom('%H:%M', true) }}–{{ as_timestamp(p.delivery_window_end)|timestamp_custom('%H:%M', true) }}{% endif %}{% endif %}<br>
  **Kollinummer:** `{{ p.kollinummer }}`<br>
  **Sendingsnummer:** `{{ p.sendingsnummer }}`<br>
  **Mottaker:** {{ p.recipient }}{% if p.recipient_address %}, {{ p.recipient_address }}{% endif %}{% if p.recipient_city %} {{ p.recipient_city }}{% endif %}<br>
  **Vekt:** {{ p.weight_kg or '—' }} kg · **Størrelse:** {{ p.dimensions or '—' }}

  **Sporing:**
  {% for e in p.tracking %}
  - {{ as_timestamp(e.time)|timestamp_custom('%d.%m %H:%M', true) }} — {{ e.description }}{% if e.location %} ({{ e.location }}){% endif %}
  {%- endfor %}

  ---
  {% endfor %}
```

For an auto-updating per-parcel list you can also install the
[auto-entities](https://github.com/thomasloven/lovelace-auto-entities) custom
card and filter on `integration: parcel_tracker`.

---

## Options

Configure via the integration's **Configure** button:

- **Polling interval (minutes)** — how often to refresh (minimum 5).
- **Days to keep delivered parcels** — delivered parcels older than this are
  dropped from the counts.
- **Show delivered parcels** — hide delivered parcels entirely if disabled.
- **Create individual package entities** — enable/disable per-parcel sensors.

---

## Events

The integration fires these events on the Home Assistant event bus:

- `parcel_tracker_new_package`
- `parcel_tracker_status_changed` (includes `previous_status`)
- `parcel_tracker_ready_for_pickup`
- `parcel_tracker_delivered`

Each event carries `parcel_id`, `tracking_number`, `carrier`, `status`,
`status_text`, `sender`, and `name`.

### Example automations

Notify when a parcel becomes ready for pickup:

```yaml
automation:
  - alias: "Parcel ready for pickup"
    trigger:
      - platform: event
        event_type: parcel_tracker_ready_for_pickup
    action:
      - service: notify.mobile_app
        data:
          title: "Parcel ready for pickup"
          message: >-
            {{ trigger.event.data.name or trigger.event.data.tracking_number }}
            from {{ trigger.event.data.sender }} is ready to collect.
```

Announce when something is arriving today:

```yaml
automation:
  - alias: "Parcel arriving today"
    trigger:
      - platform: state
        entity_id: sensor.parcel_tracker_arriving_today
    condition:
      - condition: numeric_state
        entity_id: sensor.parcel_tracker_arriving_today
        above: 0
    action:
      - service: notify.mobile_app
        data:
          message: >-
            {{ states('sensor.parcel_tracker_arriving_today') }} parcel(s)
            arriving today.
```

---

## Troubleshooting

- **"The authorization code was rejected."** The code is single-use and
  short-lived. Restart the login flow and paste a fresh code promptly.
- **Sensors show 0 / unavailable.** A parcel only appears once the sender has
  registered it with Posten. Also confirm the account you logged in with is the
  one receiving the parcels.
- **Re-authentication keeps appearing.** Posten may have invalidated the
  refresh token (e.g. after a password change). Complete the login flow again.
- **It stopped working after an app/backend change.** Because this uses an
  unofficial API, Posten changes can break it. Check for an integration update.
- Enable debug logging:

  ```yaml
  logger:
    default: info
    logs:
      custom_components.parcel_tracker: debug
  ```

---

## Privacy & security

- Authentication uses OAuth tokens; **your login credentials are never seen or
  stored** by the integration.
- Tokens are stored in Home Assistant's config entry storage. Diagnostics output
  **redacts** tokens and personal fields (tracking numbers, sender, pickup
  location, tracking URLs).
- All external data is treated as untrusted and parsed defensively.
- No data is sent anywhere except Posten's own endpoints.

---

## Alternatives (official API)

If you only need to track **known tracking numbers** and want a documented,
supported API, Bring offers an official **Tracking API**
(`https://developer.bring.com/api/tracking/`). It requires a Mybring account and
API key, is oriented at senders, and has **no** endpoint for listing all parcels
on a personal account — which is why this integration uses the app API instead.
A tracking-number-based provider could be added alongside this one via the
provider abstraction.

---

## Disclaimer

This project is not affiliated with, endorsed by, or supported by Posten Norge
AS or Bring. "Posten" and "Bring" are trademarks of their respective owners.
