#!/usr/bin/env bash
# Flag bare asyncio.create_task / asyncio.ensure_future calls.
#
# Reason: tasks not held by a strong reference get garbage-collected
# before they run. See docs/rules/asyncio-create-task.md for the
# canonical incident + fix pattern. Use omoi_os.utils.asyncio_tasks.
# fire_and_forget() instead.
#
# Allowed callsites:
#   - The helper itself (asyncio_tasks.py)
#   - Lines that store the result somewhere (var = , self.x = , .append(),
#     return ..., await ..., asyncio.gather(...))
#
# This is a coarse grep — false positives can be silenced by adding
# `# noqa: bare-create-task` on the line. The grep below explicitly
# allows that escape hatch.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Find lines that call create_task / ensure_future bare, excluding:
#   - the helper module itself
#   - lines with explicit `# noqa: bare-create-task`
#   - lines that obviously hold the result (assignment, append, return,
#     await, gather)
PATTERN='(asyncio\.create_task\(|asyncio\.ensure_future\()'

# grep --include keeps the search to .py files; we exclude the helper.
matches=$(
  grep -rEn --include='*.py' "$PATTERN" \
      backend/omoi_os \
    | grep -vE 'utils/asyncio_tasks\.py' \
    | grep -vE 'noqa: bare-create-task' \
    | grep -vE '(=\s*asyncio\.(create_task|ensure_future)|\.append\(\s*asyncio\.|return\s+asyncio\.|await\s+asyncio\.(create_task|ensure_future)|asyncio\.gather\()' \
    || true
)

if [[ -n "$matches" ]]; then
  echo "✗ bare asyncio.create_task / asyncio.ensure_future call(s) found:"
  echo
  echo "$matches"
  echo
  echo "Use omoi_os.utils.asyncio_tasks.fire_and_forget() instead."
  echo "See docs/rules/asyncio-create-task.md for the why."
  echo "Silence with `# noqa: bare-create-task` only when the result is"
  echo "stored in a place this grep can't see (instance method, etc.)."
  exit 1
fi

echo "✓ no bare asyncio.create_task callsites"
