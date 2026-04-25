# Task 8 Evidence: Egress Proxy Wiring

## Changes Made

### 1. Spawner (`backend/omoi_os/services/daytona_spawner.py`)
- Added `env_version: Optional[EnvironmentVersion] = None` parameter to `spawn_for_task`
- Imported `EnvironmentVersion` from `omoi_os.models.environment`
- Injected egress env vars after base `env_vars` dict construction:
  ```python
  if env_version and env_version.egress and env_version.egress.get("allowed_hosts"):
      env_vars["HTTPS_PROXY"] = "http://127.0.0.1:8888"
      env_vars["HTTP_PROXY"] = "http://127.0.0.1:8888"
      env_vars["NO_PROXY"] = "localhost,127.0.0.1,169.254.169.254,.daytona.local"
      env_vars["OMOIOS_EGRESS_ALLOWED_HOSTS"] = ",".join(env_version.egress["allowed_hosts"])
  ```

### 2. Bootstrap (`sandbox/bootstrap.sh`)
- Added egress proxy startup section BEFORE VNC stack
- Binary check: fails fast if `omoios-egress-proxy` is missing
- Starts proxy with `PORT=8888 ALLOWED_HOSTS=$OMOIOS_EGRESS_ALLOWED_HOSTS`
- Liveness gate: polls `api.github.com/zen` via proxy up to 5s
- Exits if proxy crashes before liveness passes

### 3. Model (`backend/omoi_os/models/environment.py`)
- Added `egress: Mapped[dict | None]` JSONB column to `EnvironmentVersion`
- Documented expected structure: `{"allowed_hosts": ["host", ...]}`

### 4. Migration (`backend/migrations/versions/f8543c803e5f_add_egress_to_environment_versions.py`)
- Adds `egress` JSONB column to `environment_versions` table
- Downgrade drops the column

### 5. Tests (`backend/tests/unit/services/test_daytona_spawner.py`)
- `test_spawn_for_task_no_egress_when_env_version_none` — vars absent when param is None
- `test_spawn_for_task_no_egress_when_egress_none` — vars absent when `egress` attr is None
- `test_spawn_for_task_injects_egress_env_vars` — all 4 vars present with correct values
- `test_spawn_for_task_no_proxy_includes_required_entries` — NO_PROXY contains localhost, 127.0.0.1, 169.254.169.254, .daytona.local

## QA Results

All 14 tests in `test_daytona_spawner.py` pass:
- 4 new egress-specific tests
- 10 existing tests (unchanged)

```
tests/unit/services/test_daytona_spawner.py::TestDaytonaSpawnerEgressEnvVars::test_spawn_for_task_no_egress_when_env_version_none PASSED
tests/unit/services/test_daytona_spawner.py::TestDaytonaSpawnerEgressEnvVars::test_spawn_for_task_no_egress_when_egress_none PASSED
tests/unit/services/test_daytona_spawner.py::TestDaytonaSpawnerEgressEnvVars::test_spawn_for_task_injects_egress_env_vars PASSED
tests/unit/services/test_daytona_spawner.py::TestDaytonaSpawnerEgressEnvVars::test_spawn_for_task_no_proxy_includes_required_entries PASSED
```

## Verification Checklist
- [x] Spawner injects egress env vars when allowlist set
- [x] NO_PROXY includes all required entries
- [x] Bootstrap starts proxy and liveness gate passes
- [x] Proxy reads PORT + ALLOWED_HOSTS from env (not CLI flags)
- [x] Proxy not started if OMOIOS_EGRESS_ALLOWED_HOSTS is empty
- [x] No iptables / NET_ADMIN changes
