# BetterStack Integration Reference

Complete API and configuration reference for BetterStack's three product areas: Telemetry (logs/OTLP ingestion), Error Monitoring, and Uptime. Accurate as of April 2026.

---

## Table of Contents

1. [Product Overview and Account Setup](#product-overview-and-account-setup)
2. [Authentication](#authentication)
3. [BetterStack Telemetry — OpenTelemetry Ingestion](#betterstack-telemetry--opentelemetry-ingestion)
4. [BetterStack Telemetry — HTTP Log and Metric Ingestion](#betterstack-telemetry--http-log-and-metric-ingestion)
5. [BetterStack Telemetry — REST API](#betterstack-telemetry--rest-api)
6. [BetterStack Error Monitoring](#betterstack-error-monitoring)
7. [BetterStack Uptime — REST API](#betterstack-uptime--rest-api)
8. [Webhooks and Outbound Integrations](#webhooks-and-outbound-integrations)
9. [Official SDKs and Terraform Providers](#official-sdks-and-terraform-providers)
10. [CLI Tools and the Collector](#cli-tools-and-the-collector)
11. [Rate Limits and Payload Limits](#rate-limits-and-payload-limits)
12. [Common Gotchas](#common-gotchas)
13. [Source Index](#source-index)

---

## Product Overview and Account Setup

BetterStack bundles three distinct products under one platform:

| Product | Former Name | What it does |
|---------|-------------|--------------|
| **Telemetry** | Logtail / Logs | Log ingestion, OTLP traces/metrics/logs, dashboards, alerts |
| **Errors** | — (GA April 2026) | Exception tracking via Sentry-compatible DSN |
| **Uptime** | Better Uptime | HTTP monitors, heartbeats, status pages, on-call, incidents |

All products share the same `betterstack.com` login. API tokens are managed at:

- **Global API tokens** (cross-product, cross-team): `betterstack.com/settings/global-api-tokens`
- **Team-scoped tokens**: `betterstack.com/settings/api-tokens/0` → select team → choose scope (Uptime or Telemetry/Errors/Warehouse)

---

## Authentication

All BetterStack REST APIs and data ingestion endpoints use **Bearer token authentication**.

```
Authorization: Bearer <your-token>
```

There are three token types:

| Token type | Scope | Where to create |
|------------|-------|-----------------|
| **Global API token** | All teams, all products | `betterstack.com/settings/global-api-tokens` |
| **Uptime API token** | One team, Uptime resources only | API tokens → Team-based tokens → Uptime |
| **Telemetry API token** | One team, Telemetry + Errors + Warehouse | API tokens → Team-based tokens → Telemetry |

**Source token** (different from API token): a per-source credential embedded in your app for data ingestion only. It authenticates log/metric/trace pushes to `$INGESTING_HOST`. Not the same as an API management token. Found on the source detail page in the Telemetry dashboard, or returned by `POST /api/v1/sources`.

All APIs follow the **JSON:API specification** (`Content-Type: application/vnd.api+json` for writes, standard JSON for GET responses).

---

## BetterStack Telemetry — OpenTelemetry Ingestion

### Base Ingestion Endpoints

BetterStack accepts OTLP/HTTP (not gRPC) directly at a single hostname:

```
https://in-otel.logs.betterstack.com
```

Signal-specific paths:

| Signal | Endpoint |
|--------|----------|
| Traces | `https://in-otel.logs.betterstack.com/v1/traces` |
| Logs | `https://in-otel.logs.betterstack.com/v1/logs` |
| Metrics | `https://in-otel.logs.betterstack.com/v1/metrics` |

**Important**: The `in-otel.logs.betterstack.com` hostname is documented as the global OTLP endpoint, but **per-source tokens authenticate only against the source-specific ingesting host** (e.g., `s95.eu-nbg-2.betterstackdata.com/v1/metrics`). Sending OTLP with a source token to `in-otel.logs.betterstack.com` returns `401 Unauthorized` (verified 2026-04-26). Use the source-specific `ingesting_host` for OTLP traces/metrics/logs and you get a `200`. The global hostname appears to be reserved for team-level Telemetry API tokens.

### Authentication for OTLP

Pass the **source token** (not the API management token) in the Authorization header:

```
Authorization: Bearer <source-token>
```

### Environment Variables (Standard OTEL SDK)

```bash
# Required
export OTEL_EXPORTER_OTLP_ENDPOINT="https://in-otel.logs.betterstack.com"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <source-token>"

# Recommended
export OTEL_SERVICE_NAME="my-service"
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=production"
```

For signal-specific overrides:

```bash
# Override only traces
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="https://in-otel.logs.betterstack.com/v1/traces"
export OTEL_EXPORTER_OTLP_TRACES_HEADERS="Authorization=Bearer <source-token>"

# Override only logs
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT="https://in-otel.logs.betterstack.com/v1/logs"
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="Authorization=Bearer <source-token>"

# Override only metrics
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT="https://in-otel.logs.betterstack.com/v1/metrics"
export OTEL_EXPORTER_OTLP_METRICS_HEADERS="Authorization=Bearer <source-token>"
```

### OpenTelemetry Collector Configuration

If routing through an OTel Collector, configure an `otlphttp` exporter:

```yaml
# otel-collector-config.yaml
exporters:
  otlphttp/betterstack:
    endpoint: "https://in-otel.logs.betterstack.com"
    headers:
      Authorization: "Bearer <source-token>"
    compression: gzip
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
    sending_queue:
      enabled: true
      num_consumers: 4
      queue_size: 100

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlphttp/betterstack]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlphttp/betterstack]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlphttp/betterstack]
```

### Downloading Pre-filled Collector Config

BetterStack generates a ready-to-use collector config per source:

```bash
curl https://telemetry.betterstack.com/otel/<source-token> -o otel-config.yaml
```

### Python SDK (FastAPI / any OTLP-compatible framework)

```python
# pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "my-fastapi-app",
    "deployment.environment": "production",
})

exporter = OTLPSpanExporter(
    endpoint="https://in-otel.logs.betterstack.com/v1/traces",
    headers={"Authorization": "Bearer <source-token>"},
)

provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
```

### Trace-Log Correlation

To correlate traces with logs, both datasets must share identical fields:

- `span.trace_id` — must match between spans and logs
- `span.span_id` — must match between spans and logs
- Both must go to the **same telemetry source** (same source token)
- Log timestamps must fall within the span's duration window

If your log library uses different field names (e.g., `context.trace_id`), use a VRL transformation on the source to rename them:

```vrl
.span.trace_id = del(.context.trace_id)
```

### gRPC Note

BetterStack's cloud ingest endpoint does **not** expose native gRPC. Use OTLP/HTTP. If you run the BetterStack Collector locally (see [CLI Tools](#cli-tools-and-the-collector)), the collector itself exposes local gRPC on port `4317` and HTTP on port `4318`, then forwards to BetterStack over HTTPS.

**Sources**: [Better Stack OpenTelemetry docs](https://betterstack.com/docs/logs/open-telemetry/), [OneUptime OTLP guide](https://oneuptime.com/blog/post/2026-02-06-otel-better-stack-otlp-source-token/view), [Better Stack tracing docs](https://betterstack.com/docs/logs/tracing/)

---

## BetterStack Telemetry — HTTP Log and Metric Ingestion

These are direct HTTP ingestion endpoints that do not require OTel SDK. Useful for raw log shipping.

### Log Ingestion

```
POST https://<ingesting-host>
```

The `<ingesting-host>` is source-specific, returned when creating a source. Example: `s95.eu-nbg-2.betterstackdata.com`.

```bash
# Single log event
curl -X POST "https://<ingesting-host>" \
  -H "Authorization: Bearer <source-token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "User logged in", "user_id": 42, "level": "info"}'

# Multiple events (JSON array)
curl -X POST "https://<ingesting-host>" \
  -H "Authorization: Bearer <source-token>" \
  -H "Content-Type: application/json" \
  -d '[{"message": "event A"},{"message": "event B"}]'

# With custom timestamp (dt field)
curl -X POST "https://<ingesting-host>" \
  -H "Authorization: Bearer <source-token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "past event", "dt": "2024-01-15T12:00:00Z"}'
```

**Content types supported**: `application/json`, `application/x-ndjson`, `application/msgpack`

**Timestamp field** (`dt`) accepts:
- UNIX seconds: `1672490759`
- UNIX milliseconds: `1672490759123`
- UNIX nanoseconds: `1672490759123456000`
- RFC 3339: `"2023-08-09T07:03:30.123456Z"`

**Response codes**:

| Code | Meaning |
|------|---------|
| 202 | Accepted |
| 402 | Quota exceeded |
| 403 | Invalid source token |
| 406 | Invalid JSON / MessagePack format |
| 413 | Payload exceeds size limit |

**Size limits**: Maximum 10 MiB compressed per request. Individual records recommended under 100 KiB. No limit on request frequency.

### Metric Ingestion

```
POST https://<ingesting-host>/metrics
```

```bash
curl -X POST "https://<ingesting-host>/metrics" \
  -H "Authorization: Bearer <source-token>" \
  -H "Content-Type: application/json" \
  -d '[{"name":"request_count","counter":{"value":1},"tags":{"endpoint":"/api/v1/users"}}]'
```

**Metric types**:

| Type | JSON key | Description |
|------|----------|-------------|
| Gauge | `"gauge": {"value": 42}` | Point-in-time value |
| Counter | `"counter": {"value": 1}` | Monotonically increasing |
| Histogram | `"histogram": {...}` | Sampled observations with buckets |
| Summary | `"summary": {...}` | Pre-calculated quantiles |

Optional fields per metric: `dt` (timestamp), `tags` (object of label key-value pairs).

**Sources**: [BetterStack log ingestion docs](https://betterstack.com/docs/logs/ingesting-data/http/logs/), [BetterStack metrics ingestion docs](https://betterstack.com/docs/logs/ingesting-data/http/metrics/)

---

## BetterStack Telemetry — REST API

**Base URL**: `https://telemetry.betterstack.com/api/v1` (Sources)
**Base URL**: `https://telemetry.betterstack.com/api/v2` (Dashboards, Alerts, Explorations)

All endpoints require `Authorization: Bearer <telemetry-api-token>`.

### Sources

A "source" is a logical data stream with its own token and ingesting host. Create one per application or signal type.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/sources` | List all sources (paginated, max 50/page) |
| GET | `/api/v1/sources/{id}` | Get a single source |
| POST | `/api/v1/sources` | Create a source |
| PATCH | `/api/v1/sources/{id}` | Update a source |
| DELETE | `/api/v1/sources/{id}` | Delete a source |

**Create source — key request parameters**:

| Parameter | Type | Notes |
|-----------|------|-------|
| `name` | string | Required. Display name. |
| `platform` | string | Required. E.g., `http`, `nginx`, `prometheus`, `docker`, `kubernetes`, `opentelemetry` |
| `data_region` | string | `us_east`, `germany`, `singapore` |
| `logs_retention` | integer | Retention days for logs |
| `metrics_retention` | integer | Retention days for metrics |
| `vrl_transformation` | string | VRL code for event transformation at ingest |
| `source_group_id` | integer | Group this source belongs to |
| `ingesting_paused` | boolean | Pause ingestion without deleting |
| `scrape_urls` | array | For `prometheus_scrape` platform: URLs to scrape |
| `scrape_frequency_secs` | integer | Scrape interval: 15, 30, 60, 120, or 300 |

**Create source — response fields** (critical for ingestion setup):

| Field | Description |
|-------|-------------|
| `token` | The source token for data ingestion auth |
| `ingesting_host` | Source-specific ingestion hostname (e.g., `s95.eu-nbg-2.betterstackdata.com`) |

### Dashboards

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/dashboards` | List dashboards (paginated) |
| GET | `/api/v2/dashboards/{id}` | Get dashboard with variables, charts, sections |
| POST | `/api/v2/dashboards` | Create dashboard |
| PATCH | `/api/v2/dashboards/{id}` | Update dashboard |
| DELETE | `/api/v2/dashboards/{id}` | Delete dashboard |
| GET | `/api/v2/dashboards/{id}/export` | Export dashboard config |
| POST | `/api/v2/dashboards/import` | Import dashboard config |
| GET | `/api/v2/dashboards/templates` | List available templates |

### Alerts

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/alerts` | List all alerts across dashboards and explorations (max 250/page) |
| GET | `/api/v2/alerts/{id}` | Get a single alert |
| PATCH | `/api/v2/alerts/{id}` | Update an alert |
| DELETE | `/api/v2/alerts/{id}` | Delete an alert |
| POST | `/api/v2/dashboard-alerts/create` | Create alert on a dashboard chart |
| POST | `/api/v2/exploration-alerts/create` | Create alert on an exploration |

Alert types: threshold-based and `anomaly_rrcf` (anomaly detection).

### Explorations

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/explorations` | List saved explorations |
| GET | `/api/v2/explorations/{id}` | Get a single exploration |
| POST | `/api/v2/explorations` | Create exploration |
| PATCH | `/api/v2/explorations/{id}` | Update exploration |
| DELETE | `/api/v2/explorations/{id}` | Delete exploration |

**Sources**: [BetterStack Telemetry API getting started](https://betterstack.com/docs/logs/api/getting-started/), [List sources docs](https://betterstack.com/docs/logs/api/list-all-existing-sources/), [Create source docs](https://betterstack.com/docs/logs/api/create-a-source/), [Dashboards API](https://betterstack.com/docs/logs/api/dashboards/)

---

## BetterStack Error Monitoring

Error Monitoring became generally available on April 1, 2026. It is Sentry-compatible: you point your existing Sentry SDK's DSN at BetterStack and no instrumentation code changes are needed.

### DSN Format

```
https://<application-token>@<ingesting-host>/1
```

- `<application-token>`: Found at Errors → Applications → select app → Data ingestion tab
- `<ingesting-host>`: Found at the same Data ingestion tab (source-specific, same `.betterstackdata.com` pattern as Telemetry)
- The project ID at the end (`/1`) is required by Sentry SDKs but is ignored by BetterStack. Any integer works.

### Configuration Examples

**Python (sentry-sdk)**:
```python
import sentry_sdk

sentry_sdk.init(
    dsn="https://<application-token>@<ingesting-host>/1",
    traces_sample_rate=1.0,
)
```

**JavaScript (@sentry/browser or @sentry/node)**:
```javascript
import * as Sentry from "@sentry/browser";

Sentry.init({
  dsn: "https://<application-token>@<ingesting-host>/1",
  tracesSampleRate: 1.0,
});
```

**Ruby (sentry-ruby)**:
```ruby
Sentry.init do |config|
  config.dsn = "https://<application-token>@<ingesting-host>/1"
end
```

### Supported Sentry SDK Minimum Versions

| Platform | Minimum SDK version |
|----------|---------------------|
| JavaScript | 7.0.0 |
| Python | 2.0.0 |
| Ruby | 4.0.0 |
| Java / Android | 3.0.0 |
| Cocoa (iOS / macOS) | 6.0.0 |
| .NET | 3.0.0 |
| PHP | 4.0.0 |
| Go | 0.1.0 |
| React Native | 3.0.0 |

### Errors API

The Errors API uses the same authentication as Telemetry (Global API token or Telemetry API token).

**Base URL**: `https://errors.betterstack.com/api/v1` (verified — Errors has its own host, not under `telemetry.betterstack.com`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/applications` | List error tracking applications |
| GET | `/api/v1/applications/{id}` | Get a single application |
| POST | `/api/v1/applications` | Create an application |
| PATCH | `/api/v1/applications/{id}` | Update an application |
| DELETE | `/api/v1/applications/{id}` | Delete an application |
| GET | `/api/v1/application-groups` | List application groups |

### Ingestion Model

BetterStack does **not** offer a native error SDK or OTLP-based error ingestion. The ingestion model is Sentry protocol only. If you already use `sentry-sdk`, migration is a one-line DSN change.

**Sources**: [BetterStack error tracking page](https://betterstack.com/error-tracking), [Sentry SDK integration docs](https://betterstack.com/docs/errors/collecting-errors/sentry-sdk/), [Error tracking GA announcement](https://betterstack.com/community/blog/error-tracking-prime-time/), [Errors API getting started](https://betterstack.com/docs/errors/api/getting-api-token/)

---

## BetterStack Uptime — REST API

**Base URL**: `https://uptime.betterstack.com`

Most resources use `/api/v2/`. Incidents, escalation policies, and metadata use `/api/v3/`. Heartbeat pinging uses `/api/v1/`.

All endpoints require `Authorization: Bearer <uptime-api-token>`.

The API follows JSON:API spec. Paginated list responses return a `pagination` object with `first`, `last`, `prev`, `next` links. Default page size is 10; maximum is 50.

---

### Monitors

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/monitors` | List all monitors |
| GET | `/api/v2/monitors/{id}` | Get a single monitor |
| POST | `/api/v2/monitors` | Create a monitor |
| PATCH | `/api/v2/monitors/{id}` | Update a monitor |
| DELETE | `/api/v2/monitors/{id}` | Delete a monitor |
| GET | `/api/v2/monitors/{id}/sla` | Get SLA / availability summary |

**List monitors — query parameters**: `team_name`, `url`, `pronounceable_name`

**Monitor object fields** (partial):

| Field | Type | Notes |
|-------|------|-------|
| `url` | string | URL being monitored |
| `monitor_type` | string | `status` (HTTP), `keyword`, `tcp`, `udp`, `ping`, `smtp`, `pop`, `imap`, `dns` |
| `status` | string | `paused`, `pending`, `maintenance`, `up`, `validating`, `down` |
| `check_frequency` | integer | Seconds between checks |
| `regions` | array | `us`, `eu`, `as`, `au` |
| `http_method` | string | `GET`, `POST`, `PUT`, etc. |
| `required_keyword` | string | Keyword to look for (keyword monitor type) |
| `verify_ssl` | boolean | Check SSL validity |
| `request_timeout` | integer | Request timeout in seconds |
| `recovery_period` | integer | Seconds before incident is created after failure |
| `confirmation_period` | integer | Seconds of failure before alerting |
| `expected_status_codes` | array | HTTP status codes considered healthy |
| `request_headers` | array | Array of `{id, name, value}` objects |
| `request_body` | string | POST body content |
| `policy_id` | integer | Escalation policy ID |
| `call`, `sms`, `email`, `push` | boolean | Alert channels |
| `ssl_expiration` | integer | Days before SSL expiry alert |
| `domain_expiration` | integer | Days before domain expiry alert |
| `maintenance_from`, `maintenance_to` | string | Maintenance window times (HH:MM) |
| `maintenance_timezone` | string | Timezone for maintenance window |
| `maintenance_days` | array | Days of week for maintenance window |

---

### Monitor Groups

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/monitor-groups` | List all monitor groups |
| GET | `/api/v2/monitor-groups/{id}` | Get a single monitor group |
| GET | `/api/v2/monitor-groups/{id}/monitors` | List monitors in a group |
| POST | `/api/v2/monitor-groups` | Create a monitor group |
| PATCH | `/api/v2/monitor-groups/{id}` | Update a monitor group |
| DELETE | `/api/v2/monitor-groups/{id}` | Delete a monitor group |

---

### Heartbeats

**Heartbeat ping URL** (not a management endpoint — this is what your cron job calls):

```
GET https://uptime.betterstack.com/api/v1/heartbeat/<heartbeat-token>
```

To signal a failure explicitly:
```
GET https://uptime.betterstack.com/api/v1/heartbeat/<heartbeat-token>/fail
```

To pass an exit code from a cron job:
```bash
# In a shell script — $? captures the previous command's exit code
curl "https://uptime.betterstack.com/api/v1/heartbeat/<heartbeat-token>/$?"
```

Period and grace period are configured in the dashboard when creating the heartbeat — they are not URL parameters.

**Management endpoints**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/heartbeats` | List all heartbeats |
| GET | `/api/v2/heartbeats/{id}` | Get a single heartbeat |
| GET | `/api/v2/heartbeats/{id}/availability` | Get heartbeat availability summary |
| POST | `/api/v2/heartbeats` | Create a heartbeat |
| PATCH | `/api/v2/heartbeats/{id}` | Update a heartbeat |
| DELETE | `/api/v2/heartbeats/{id}` | Delete a heartbeat |

**Create heartbeat — parameters**:

| Parameter | Type | Notes |
|-----------|------|-------|
| `name` | string | Required |
| `period` | integer | Seconds between expected pings (minimum 30) |
| `grace` | integer | Grace period before marking down, in seconds |
| `policy_id` | integer | Escalation policy |
| `call`, `sms`, `email`, `push` | boolean | Alert channels |
| `heartbeat_group_id` | integer | Group assignment |
| `paused` | boolean | Start paused |
| `maintenance_*` | various | Maintenance window configuration |

The response includes the `url` field containing the full heartbeat ping URL.

---

### Heartbeat Groups

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/heartbeat-groups` | List all heartbeat groups |
| GET | `/api/v2/heartbeat-groups/{id}` | Get a single heartbeat group |
| GET | `/api/v2/heartbeat-groups/{id}/heartbeats` | List heartbeats in a group |
| POST | `/api/v2/heartbeat-groups` | Create a heartbeat group |
| PATCH | `/api/v2/heartbeat-groups/{id}` | Update a heartbeat group |
| DELETE | `/api/v2/heartbeat-groups/{id}` | Delete a heartbeat group |

---

### Incidents

**Note: Incidents use API v3.**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v3/incidents` | List incidents (filterable, paginated) |
| GET | `/api/v3/incidents/{id}` | Get a single incident |
| GET | `/api/v3/incidents/{id}/timeline` | List incident timeline events |
| POST | `/api/v3/incidents` | Create an incident manually |
| POST | `/api/v3/incidents/{id}/acknowledge` | Acknowledge an active incident |
| POST | `/api/v3/incidents/{id}/resolve` | Resolve an active incident |
| POST | `/api/v3/incidents/{id}/reopen` | Reopen a resolved incident |
| POST | `/api/v3/incidents/{id}/escalate` | Escalate an ongoing incident |
| DELETE | `/api/v3/incidents/{id}` | Delete an incident |

**List incidents — query parameters**:

| Parameter | Type | Notes |
|-----------|------|-------|
| `team_name` | string | Filter by team |
| `from` | date | `YYYY-MM-DD` start date |
| `to` | date | `YYYY-MM-DD` end date |
| `monitor_id` | integer | Filter by monitor |
| `heartbeat_id` | integer | Filter by heartbeat |
| `resolved` | boolean | `?resolved=false` for active incidents |
| `acknowledged` | boolean | Filter by ack status |
| `metadata` | nested | Filter by metadata key-value pairs |

Default page size: 10; max: 50.

---

### Incident Comments

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/incidents/{incident_id}/comments` | List all comments on an incident |
| POST | `/api/v2/incidents/{incident_id}/comments` | Add a comment |
| PATCH | `/api/v2/incidents/{incident_id}/comments/{id}` | Update a comment |
| DELETE | `/api/v2/incidents/{incident_id}/comments/{id}` | Delete a comment |

---

### Metadata

**Note: Metadata uses API v3.** Metadata is key-value data attached to monitors, heartbeats, incidents, webhooks, and email integrations.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v3/metadata` | List metadata (filter by owner_id, owner_type, team_name) |
| POST | `/api/v3/metadata` | Create/update metadata |

---

### Escalation Policies

**Note: Escalation policies use API v3.**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v3/policies` | List escalation policies |
| GET | `/api/v3/policies/{id}` | Get a single policy |
| POST | `/api/v3/policies` | Create a policy |
| PATCH | `/api/v3/policies/{id}` | Update a policy |
| DELETE | `/api/v3/policies/{id}` | Delete a policy |

**Policy object fields**:

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | Policy name |
| `repeat_count` | integer | How many times to repeat the policy |
| `repeat_delay` | integer | Seconds between repetitions |
| `incident_token` | string | Unique token for this policy |
| `steps` | array | Ordered escalation steps |

**Step types**:

- `escalation`: Notifies specified members or integrations. Contains `wait_before` (seconds) and `step_members` (e.g., `"current_on_call"`, `"all_slack_integrations"`)
- `time_branching`: Routes to different policies based on time-of-day or day-of-week conditions

---

### On-Call Schedules

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/on-calls` | List all on-call schedules |
| GET | `/api/v2/on-calls/{id}` | Get a single schedule |
| POST | `/api/v2/on-calls` | Create a schedule |
| PATCH | `/api/v2/on-calls/{id}` | Update a schedule |
| DELETE | `/api/v2/on-calls/{id}` | Delete a schedule |

**Related on-call sub-resources**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/on-calls/{id}/events` | List on-call calendar events |
| GET | `/api/v2/on-calls/{id}/rotations` | List rotations for a schedule |
| POST | `/api/v2/on-calls/{id}/rotations` | Create a rotation |
| PATCH | `/api/v2/on-calls/{id}/rotations/{rid}` | Update a rotation |
| DELETE | `/api/v2/on-calls/{id}/rotations/{rid}` | Delete a rotation |

---

### Severities

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/severities` | List all severity levels |
| GET | `/api/v2/severities/{id}` | Get a single severity |
| POST | `/api/v2/severities` | Create a severity |
| PATCH | `/api/v2/severities/{id}` | Update a severity |
| DELETE | `/api/v2/severities/{id}` | Delete a severity |

---

### Status Pages

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/status-pages` | List all status pages |
| GET | `/api/v2/status-pages/{id}` | Get a single status page |
| POST | `/api/v2/status-pages` | Create a status page |
| PATCH | `/api/v2/status-pages/{id}` | Update a status page |
| DELETE | `/api/v2/status-pages/{id}` | Delete a status page |

**Status page sub-resources**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/status-pages/{id}/sections` | List sections on a status page |
| POST | `/api/v2/status-pages/{id}/sections` | Create a section |
| PATCH | `/api/v2/status-pages/{id}/sections/{sid}` | Update a section |
| DELETE | `/api/v2/status-pages/{id}/sections/{sid}` | Delete a section |
| GET | `/api/v2/status-pages/{id}/resources` | List resources on a status page |
| POST | `/api/v2/status-pages/{id}/resources` | Add a resource to a status page |
| PATCH | `/api/v2/status-pages/{id}/resources/{rid}` | Update a resource |
| DELETE | `/api/v2/status-pages/{id}/resources/{rid}` | Remove a resource |
| GET | `/api/v2/status-pages/{id}/status-reports` | List incident reports |
| POST | `/api/v2/status-pages/{id}/status-reports` | Create an incident report |
| PATCH | `/api/v2/status-pages/{id}/status-reports/{rid}` | Update a report |
| DELETE | `/api/v2/status-pages/{id}/status-reports/{rid}` | Delete a report |
| GET | `/api/v2/status-pages/{id}/status-reports/{rid}/updates` | List report updates |
| POST | `/api/v2/status-pages/{id}/status-reports/{rid}/updates` | Add a report update |
| PATCH | `/api/v2/status-pages/{id}/status-reports/{rid}/updates/{uid}` | Edit an update |
| DELETE | `/api/v2/status-pages/{id}/status-reports/{rid}/updates/{uid}` | Delete an update |

**Status page groups** (for organizing multiple status pages):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/status-page-groups` | List status page groups |
| POST | `/api/v2/status-page-groups` | Create a group |
| PATCH | `/api/v2/status-page-groups/{id}` | Update a group |
| DELETE | `/api/v2/status-page-groups/{id}` | Delete a group |

**Create/update status page — key parameters**:

| Parameter | Type | Notes |
|-----------|------|-------|
| `company_name` | string | Displayed on the page |
| `subdomain` | string | `.betteruptime.com` subdomain (must be unique) |
| `custom_domain` | string | Your own domain (requires CNAME setup) |
| `timezone` | string | Rails TimeZone format (e.g., `"UTC"`) |
| `history` | integer | Days of history shown: 7–365 |
| `design` | string | `"v1"` or `"v2"` |
| `theme` | string | `"light"`, `"dark"`, `"system"` |
| `password_enabled` | boolean | Password-protect the page |
| `password` | string | Required if `password_enabled: true` |
| `ip_allowlist` | array | IP/CIDR ranges for access restriction |
| `subscribable` | boolean | Allow email/webhook subscriptions |
| `whitelabeled` | boolean | Remove BetterStack branding (billable) |
| `google_analytics_id` | string | GA tracking ID |
| `custom_css`, `custom_javascript` | string | Custom styling/scripting |
| `announcement` | string | Banner announcement text |

**Custom domain CNAME setup**:
- Create a CNAME record pointing your subdomain (e.g., `status.yourdomain.com`) to `statuspage.betteruptime.com`
- Propagation: up to 72 hours
- Cloudflare users: must use DNS-only mode (gray cloud), not proxied mode

---

### Integration Endpoints

All integration types support standard CRUD (GET list, GET single, POST, PATCH, DELETE). Base path pattern: `/api/v2/<integration-type>`.

| Integration type | Path prefix |
|-----------------|-------------|
| Email (incoming alerts) | `/api/v2/email-integrations` |
| Incoming webhooks | `/api/v2/incoming-webhooks` |
| Outgoing webhooks | `/api/v2/outgoing-webhooks` |
| Slack | `/api/v2/slack-integrations` |
| PagerDuty | `/api/v2/pagerduty-integrations` |
| Splunk On-Call | `/api/v2/splunk-on-call-integrations` |
| New Relic | `/api/v2/new-relic-integrations` |
| Datadog | `/api/v2/datadog-integrations` |
| AWS CloudWatch | `/api/v2/aws-cloudwatch-integrations` |
| Microsoft Azure | `/api/v2/azure-integrations` |
| Google Monitoring | `/api/v2/google-monitoring-integrations` |
| Grafana | `/api/v2/grafana-integrations` |
| Elastic | `/api/v2/elastic-integrations` |
| Prometheus | `/api/v2/prometheus-integrations` |
| Atlassian Jira | `/api/v2/jira-integrations` |
| Catalog | `/api/v2/catalog-integrations` |

**Email integration** is an *incoming* integration — BetterStack assigns a unique inbox address (e.g., `test@incidents.uptime.betterstack.com`). Configure rules to parse the email body and create/resolve incidents automatically.

**Incoming webhook** — BetterStack generates a unique URL. Your external tool POSTs to it. Configure rules to extract incident title, cause, alert ID, and status from the JSON payload.

---

### Team Members

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/team-members` | List all members and pending invitations |
| GET | `/api/v2/team-members/{id}` | Get a single team member |
| POST | `/api/v2/team-members` | Invite a team member |
| DELETE | `/api/v2/team-members/{id}` | Remove by ID |
| DELETE | `/api/v2/team-members` | Remove by email (`?email=...`) |

Query parameters: `team_name` (required for global tokens), `email` (filter).

**Sources**: [Monitors API](https://betterstack.com/docs/uptime/api/list-all-existing-monitors/), [Heartbeats API](https://betterstack.com/docs/uptime/api/list-all-existing-hearbeats/), [Incidents API](https://betterstack.com/docs/uptime/api/list-all-incidents/), [Status pages API](https://betterstack.com/docs/uptime/api/list-all-existing-status-pages/), [Escalation policies API](https://betterstack.com/docs/uptime/api/escalation-policies/), [Elastic integrations (for nav reference)](https://betterstack.com/docs/uptime/api/list-all-elastic-integrations/)

---

## Webhooks and Outbound Integrations

### Outgoing Webhook Configuration

Outgoing webhooks are configured under Uptime → Integrations → Exporting data. They deliver to any HTTPS endpoint.

**Management API**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v2/outgoing-webhooks` | List outgoing webhooks |
| GET | `/api/v2/outgoing-webhooks/{id}` | Get a single webhook |
| POST | `/api/v2/outgoing-webhooks` | Create a webhook |
| PATCH | `/api/v2/outgoing-webhooks/{id}` | Update a webhook |
| DELETE | `/api/v2/outgoing-webhooks/{id}` | Delete a webhook |

**Configuration fields**:

| Field | Description |
|-------|-------------|
| `name` | Identifier |
| `url` | Target HTTPS endpoint |
| `trigger_type` | What event fires this webhook |
| `http_method` | e.g., `"post"` |
| `headers_template` | Custom HTTP headers to include |
| `body_template` | Custom JSON body template |
| `auth_username` / `auth_password` | HTTP Basic Auth credentials |

**Trigger types**: `incident_change`, `on_call_change`, and fine-grained variants: `on_incident_started`, `on_incident_acknowledged`, `on_incident_resolved`, `monitor_change`.

### Delivery Behavior

- **Protocol**: HTTPS only
- **Method**: POST
- **Format**: JSON body
- **Success**: any 2xx HTTP status code
- **Timeout**: 30 seconds maximum per delivery attempt
- **Retries**: BetterStack retries with exponential backoff on failures
- **Signing**: BetterStack does **not** currently provide HMAC payload signing for outgoing webhooks. Secure your endpoint by IP allowlisting or using a secret path component in the URL.

### Status Page Subscription Webhooks

Users can subscribe to status page updates via webhook. BetterStack pushes these events:

**HTTP headers on each delivery**:
```
Content-Type: application/json
User-Agent: BetterStack-StatusPage/1.0
X-BetterUptime-Event: incident | maintenance | component_update
```

**Incident event payload**:
```json
{
  "event_type": "incident",
  "meta": {
    "unsubscribe": "https://...",
    "documentation": "https://..."
  },
  "page": {
    "id": "string",
    "status_indicator": "downtime|degraded|operational|maintenance",
    "status_description": "string"
  },
  "incident": {
    "id": "string",
    "name": "string",
    "created_at": "2024-01-15T12:00:00Z",
    "updated_at": "2024-01-15T12:05:00Z",
    "shortlink": "https://...",
    "organization_id": "string",
    "incident_updates": [
      {
        "id": "string",
        "status_report_id": "string",
        "body": "We are investigating...",
        "created_at": "2024-01-15T12:00:00Z",
        "updated_at": "2024-01-15T12:00:00Z"
      }
    ]
  }
}
```

**Component update event payload**:
```json
{
  "event_type": "component_update",
  "component": {
    "id": "string",
    "name": "API",
    "status": "operational|degraded|downtime",
    "previous_status": "degraded",
    "updated_at": "2024-01-15T12:05:00Z"
  }
}
```

**Sources**: [Outgoing webhooks docs](https://betterstack.com/docs/uptime/webhooks/), [Status page webhook subscription docs](https://betterstack.com/docs/uptime/subscribing-to-status-updates/subscribing-with-webhooks/)

---

## Official SDKs and Terraform Providers

### Python Logging SDK

**Package**: `logtail-python`
**GitHub**: https://github.com/logtail/logtail-python (under the `logtail` GitHub org, owned by BetterStack)
**PyPI**: https://pypi.org/project/logtail-python/
**Latest**: 0.3.4 (September 2025)
**Requires**: Python 3.7+

```bash
pip install logtail-python
```

```python
from logtail import LogtailHandler
import logging

handler = LogtailHandler(
    source_token="<source-token>",
    host="https://<ingesting-host>",  # e.g., https://s95.eu-nbg-2.betterstackdata.com
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Structured logging
logger.info("Payment processed", extra={"amount": 99.99, "currency": "USD"})

# Context manager for shared fields
import logtail
with logtail.context(request_id="abc-123"):
    logger.info("Processing request")
    logger.error("Request failed")
```

**Django integration** (add to `settings.py`):
```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "betterstack": {
            "class": "logtail.LogtailHandler",
            "source_token": "<source-token>",
            "host": "https://<ingesting-host>",
        },
    },
    "root": {"handlers": ["betterstack"], "level": "INFO"},
}
```

### Other Language SDKs

All live under the `logtail` GitHub org (https://github.com/logtail):

| Language | Package / Repo |
|----------|---------------|
| Node.js | `@logtail/node` — https://github.com/logtail/logtail-js |
| Browser JS | `@logtail/browser` — https://github.com/logtail/logtail-js |
| Ruby | `logtail-ruby` — https://github.com/logtail/logtail-ruby |
| Ruby Rack | `logtail-ruby-rack` |
| Go | https://github.com/logtail/logtail-go |

### Terraform Providers

**Uptime provider** (`BetterStackHQ/better-uptime`):

```hcl
terraform {
  required_providers {
    betteruptime = {
      source  = "BetterStackHQ/better-uptime"
      version = "~> 0.20"
    }
  }
}

provider "betteruptime" {
  api_token = var.betterstack_api_token
}

resource "betteruptime_monitor" "api" {
  monitor_type     = "status"
  url              = "https://api.example.com/health"
  check_frequency  = 60
  email            = true
}

resource "betteruptime_heartbeat" "worker" {
  name   = "background-worker"
  period = 300
  grace  = 60
}
```

Registry: https://registry.terraform.io/providers/BetterStackHQ/better-uptime/latest
GitHub: https://github.com/BetterStackHQ/terraform-provider-better-uptime

**Telemetry provider** (`BetterStackHQ/logtail`):

```hcl
terraform {
  required_providers {
    logtail = {
      source  = "BetterStackHQ/logtail"
      version = "~> 0.1"
    }
  }
}

resource "logtail_source" "app_logs" {
  name     = "my-app"
  platform = "http"
}
```

Registry: https://registry.terraform.io/providers/BetterStackHQ/logtail/latest
GitHub: https://github.com/BetterStackHQ/terraform-provider-logtail

### Community Python Uptime Client

Unofficial Python package for the Uptime management API:
- PyPI: `betterstack-uptime` — https://pypi.org/project/betterstack-uptime/

### No Official CLI

BetterStack does **not** ship a standalone CLI for log tailing or monitor management. The `collector` (see next section) has a CLI-like install script but is a daemon, not an interactive tool.

**Sources**: [logtail-python GitHub](https://github.com/logtail/logtail-python), [logtail GitHub org](https://github.com/logtail), [BetterStackHQ GitHub](https://github.com/BetterStackHQ), [Terraform uptime registry](https://registry.terraform.io/providers/BetterStackHQ/better-uptime/latest)

---

## CLI Tools and the Collector

### BetterStack Collector

The Collector is BetterStack's official eBPF-based agent for zero-code log, metric, and trace collection. It is the recommended ingestion path for Kubernetes and Docker environments.

**GitHub**: https://github.com/BetterStackHQ/collector
**Helm chart**: https://github.com/BetterStackHQ/collector-helm-chart

**Requirements**: Linux kernel 5.14+ with BTF and CO-RE support (for eBPF mode).

**Installation**:

```bash
# Docker Compose (installs as a service)
curl -sSL https://raw.githubusercontent.com/BetterStackHQ/collector/main/install.sh | \
  COLLECTOR_SECRET="<collector-secret>" bash

# Kubernetes via Helm
helm repo add better-stack https://betterstackhq.github.io/collector-helm-chart
helm install better-stack-collector better-stack/collector \
  --set collector.env.COLLECTOR_SECRET="<collector-secret>"

# Docker Swarm
curl -sSL https://raw.githubusercontent.com/BetterStackHQ/collector/refs/heads/main/deploy-to-swarm.sh | \
  MANAGER_NODE=root@swarm-manager COLLECTOR_SECRET="<collector-secret>" bash
```

The `COLLECTOR_SECRET` is obtained from the BetterStack dashboard when creating a Collector source.

**Enabling OTLP receive** (so your apps can send to the local collector):

```bash
# Kubernetes Helm
helm upgrade better-stack-collector better-stack/collector \
  --set collectOtel.grpcPort=4317 \
  --set collectOtel.httpPort=4318
```

Once enabled, services in the same cluster send OTLP to:

| Protocol | Endpoint |
|----------|----------|
| gRPC | `http://<node-ip>:4317` |
| HTTP | `http://<node-ip>:4318` |
| Kubernetes service (HTTP) | `http://better-stack-collector-otlp.<namespace>.svc:4318` |

The collector then forwards everything to BetterStack over HTTPS using the collector secret. Your application does not need a source token when using the collector — authentication is handled by the collector.

**Sources**: [Collector docs](https://betterstack.com/docs/logs/collector/), [Collector GitHub](https://github.com/BetterStackHQ/collector)

---

## Rate Limits and Payload Limits

BetterStack does not publish explicit numeric rate limits (requests per minute/second) in their public documentation. The following limits are documented:

### Data Ingestion Limits

| Limit | Value |
|-------|-------|
| Max request size (HTTP log ingest) | 10 MiB compressed |
| Max request size (error response header) | 20 MiB |
| Recommended individual record size | < 100 KiB |
| Number of requests (HTTP log ingest) | No documented limit |
| OTLP batch size | Subject to network/infra limits; use batching with retry |

### Management API Pagination

| Endpoint family | Default page size | Max page size |
|----------------|-------------------|---------------|
| Uptime (monitors, heartbeats, status pages) | 10 | 50 |
| Incidents | 10 | 50 |
| Telemetry (sources, dashboards) | variable | 50 |
| Telemetry alerts | variable | 250 |

### Response Codes for Quota Issues

- **402**: Quota exceeded (ingestion endpoints)
- **429**: Rate limit exceeded (if encountered on management APIs)

For production workloads, BetterStack recommends using gzip compression on OTLP and batching requests. Contact `hello@betterstack.com` for enterprise rate limit discussions.

---

## Common Gotchas

### 1. `$INGESTING_HOST` Is Source-Specific, Not a Single Global Host

Each source you create gets its own `ingesting_host` value (e.g., `s95.eu-nbg-2.betterstackdata.com`). This encodes your data region. Do not hardcode `in.logs.betterstack.com` for direct HTTP log ingestion — use the host returned by the API or shown in the dashboard source settings.

For OTLP specifically, the global `in-otel.logs.betterstack.com` endpoint works, but if you want data in a specific region (Germany, Singapore, US East), use the source-specific ingesting host instead.

### 2. Source Token vs. API Token — Different Things

- **Source token**: Authenticates data *into* BetterStack (logs, metrics, traces, errors). Scoped to one source. Found in source settings / returned by `POST /api/v1/sources`.
- **API token**: Authenticates management API calls (create monitors, list incidents, etc.). Found in account settings.

Using a source token on a management API endpoint returns 401 and vice versa.

### 3. Logtail → Telemetry Rename: API Base URL Changed

The product was renamed from Logtail to Telemetry. The Telemetry management API base URL is `https://telemetry.betterstack.com/api/v1` (sources) and `https://telemetry.betterstack.com/api/v2` (dashboards, alerts). Old `logtail.com` endpoints are no longer used; all API calls go to `telemetry.betterstack.com`. The Python package is still named `logtail-python` and the Terraform provider is still `BetterStackHQ/logtail`.

### 4. Uptime API Has Mixed Versions (v2 and v3)

Most Uptime resources (monitors, heartbeats, status pages, on-call schedules, integrations) use `/api/v2/`. Incidents, escalation policies, and metadata use `/api/v3/`. Heartbeat *pinging* (the cron job call-home URL) uses `/api/v1/`. Don't assume a single version across all resources.

### 5. OTLP gRPC Is Not Available at the Cloud Endpoint

BetterStack's cloud ingestion endpoint (`in-otel.logs.betterstack.com`) only accepts OTLP/HTTP (port 443). If your SDK or collector is configured for gRPC (`grpc://...`), it will fail to connect. Switch to `http/protobuf` protocol. If you need gRPC, deploy the BetterStack Collector locally — it exposes local gRPC on 4317 and forwards over HTTPS.

### 6. Status Page CNAME Must Use a Subdomain (not apex domain)

BetterStack's CNAME target is `statuspage.betteruptime.com`. Apex/root domain CNAME records (`yourdomain.com` itself) are not universally supported by DNS. Use a subdomain like `status.yourdomain.com`. Cloudflare users must disable the proxy (use DNS-only / gray cloud) — the orange cloud proxied mode breaks SSL provisioning.

### 7. Trace-Log Correlation Requires Same Source

Logs and traces must be sent to the **same BetterStack source** (same source token) for automatic correlation. If you create separate sources for logs vs. traces, the correlation UI won't link them. Use a single source and let BetterStack distinguish signal types via the OTLP signal path (`/v1/logs` vs `/v1/traces`).

### 8. Error Monitoring Has No Native SDK

BetterStack Error Monitoring does not ship its own SDK. You must use the Sentry SDK for your language. There is no OTLP-based error ingestion path. The Sentry SDK minimum versions are strictly enforced (see the version table in the Error Monitoring section above).

### 9. Heartbeat Ping Frequency and Grace Are Dashboard-Configured, Not URL Parameters

Unlike some competitors, the heartbeat period and grace period are set when you create the heartbeat (via the dashboard or `POST /api/v2/heartbeats`). They are **not** passed as URL query parameters when pinging. Your cron job just calls the bare URL with no additional parameters.

### 10. Status Page Subscription Webhooks Have No Signing

BetterStack status page subscription webhooks do not include HMAC signatures. The `X-BetterUptime-Event` header identifies the event type but there is no cryptographic verification of payload authenticity. Secure your webhook receiver by using a secret path component or IP allowlisting BetterStack's delivery IPs.

---

## Source Index

| Topic | URL |
|-------|-----|
| OpenTelemetry ingestion docs | https://betterstack.com/docs/logs/open-telemetry/ |
| Log ingestion docs | https://betterstack.com/docs/logs/ingesting-data/http/logs/ |
| Metrics ingestion docs | https://betterstack.com/docs/logs/ingesting-data/http/metrics/ |
| Distributed tracing | https://betterstack.com/docs/logs/tracing/ |
| Collector docs | https://betterstack.com/docs/logs/collector/ |
| Telemetry API getting started | https://betterstack.com/docs/logs/api/getting-started/ |
| Telemetry Sources API | https://betterstack.com/docs/logs/api/list-all-existing-sources/ |
| Create source | https://betterstack.com/docs/logs/api/create-a-source/ |
| Python logging docs | https://betterstack.com/docs/logs/python/ |
| Error tracking product page | https://betterstack.com/error-tracking |
| Sentry SDK integration for errors | https://betterstack.com/docs/errors/collecting-errors/sentry-sdk/ |
| Error tracking GA announcement | https://betterstack.com/community/blog/error-tracking-prime-time/ |
| Errors API getting started | https://betterstack.com/docs/errors/api/getting-api-token/ |
| Uptime API getting started | https://betterstack.com/docs/uptime/api/getting-started-with-uptime-api/ |
| Monitors API | https://betterstack.com/docs/uptime/api/list-all-existing-monitors/ |
| Heartbeats API | https://betterstack.com/docs/uptime/api/list-all-existing-hearbeats/ |
| Cron & heartbeat monitor guide | https://betterstack.com/docs/uptime/cron-and-heartbeat-monitor/ |
| Incidents API | https://betterstack.com/docs/uptime/api/list-all-incidents/ |
| Status pages API | https://betterstack.com/docs/uptime/api/list-all-existing-status-pages/ |
| Escalation policies API | https://betterstack.com/docs/uptime/api/escalation-policies/ |
| Custom subdomain docs | https://betterstack.com/docs/uptime/custom-subdomain/ |
| Outgoing webhooks docs | https://betterstack.com/docs/uptime/webhooks/ |
| Incoming webhooks docs | https://betterstack.com/docs/uptime/incoming-webhooks/ |
| Status page webhook subscription | https://betterstack.com/docs/uptime/subscribing-to-status-updates/subscribing-with-webhooks/ |
| logtail-python GitHub | https://github.com/logtail/logtail-python |
| BetterStackHQ GitHub org | https://github.com/BetterStackHQ |
| Terraform Uptime provider | https://registry.terraform.io/providers/BetterStackHQ/better-uptime/latest |
| Terraform Telemetry provider | https://registry.terraform.io/providers/BetterStackHQ/logtail/latest |
| Collector GitHub | https://github.com/BetterStackHQ/collector |
| OneUptime OTLP guide (independent) | https://oneuptime.com/blog/post/2026-02-06-otel-better-stack-otlp-source-token/view |
