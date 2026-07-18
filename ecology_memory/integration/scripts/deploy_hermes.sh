#!/usr/bin/env bash
set -euo pipefail

# Multiple benchmark arms may start together. Profile deployment mutates shared container paths,
# so serialize this short copy phase; concurrent rm/cp previously produced a missing why plugin.
exec 9>"${TMPDIR:-/tmp}/dss-typed-hermes-deploy.lock"
flock 9

HERE="$(cd "$(dirname "$0")" && pwd)"
INTEGRATION="$(cd "$HERE/.." && pwd)"
MEMORY="$(cd "$INTEGRATION/.." && pwd)"
CONTAINER="${HERMES_CONTAINER:-hermes-live}"
PROFILE="${DSS_HERMES_PROFILE:-dss-eval}"
DEST="/opt/data/work/dss_typed/ecology_memory"
QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

docker ps --filter "name=^${CONTAINER}$" --filter status=running -q | grep -q . || {
  echo "deploy_hermes.sh: Hermes container '$CONTAINER' is not running; refusing to start it" >&2
  exit 2
}

if ! docker exec "$CONTAINER" hermes profile show "$PROFILE" >/dev/null 2>&1; then
  docker exec "$CONTAINER" hermes profile create "$PROFILE" --no-alias --no-skills \
    --description "Isolated Hermes comparison profile for typed, untyped, and no-scaffold runs." \
    >/dev/null
fi

# Keep the running container and the default profile untouched. The isolated profile receives the
# same provider/tool/plugin configuration, a neutral SOUL, no bundled skills, and fresh sessions.
CONFIG_STAGE="/opt/data/profiles/$PROFILE/.config.yaml.stage.$$"
docker exec "$CONTAINER" cp /opt/data/config.yaml "$CONFIG_STAGE"
docker cp "$HERE/configure_hermes_profile.py" "$CONTAINER:/tmp/configure_hermes_profile.py" >/dev/null
docker exec "$CONTAINER" python /tmp/configure_hermes_profile.py \
  "$CONFIG_STAGE"
# A benchmark process may start while another invocation refreshes the shared isolated profile.
# Publish the complete configured file with one rename so readers never observe the copied default
# file's 8K declaration between ``cp`` and configuration.
docker exec "$CONTAINER" mv "$CONFIG_STAGE" "/opt/data/profiles/$PROFILE/config.yaml"
docker exec "$CONTAINER" mkdir -p "/opt/data/profiles/$PROFILE/plugins"
for plugin in discipline why; do
  if docker exec "$CONTAINER" test -d "/opt/data/plugins/$plugin"; then
    docker exec "$CONTAINER" rm -rf "/opt/data/profiles/$PROFILE/plugins/$plugin"
    docker exec "$CONTAINER" cp -a "/opt/data/plugins/$plugin" "/opt/data/profiles/$PROFILE/plugins/$plugin"
  fi
done
docker exec "$CONTAINER" mkdir -p "/opt/data/profiles/$PROFILE/plugins/typed_bridge"
docker cp "$INTEGRATION/hermes/profile/plugins/typed_bridge/." \
  "$CONTAINER:/opt/data/profiles/$PROFILE/plugins/typed_bridge/" >/dev/null
docker cp "$INTEGRATION/hermes/profile/SOUL.md" \
  "$CONTAINER:/opt/data/profiles/$PROFILE/SOUL.md" >/dev/null

docker exec "$CONTAINER" mkdir -p \
  "$DEST/harness/questions" "$DEST/harness/data" "$DEST/hermes_bench" "$DEST/integration/runtime" "$DEST/integration/contexts" \
  "$DEST/integration/origin/connectors" "$DEST/integration/manifests" \
  "/opt/data/work/dss_typed/hermes/workspaces"

for file in connectors.py executor.py ir_schema.py llm.py origin_adapters.py parser.py synthesize.py; do
  docker cp "$MEMORY/harness/$file" "$CONTAINER:$DEST/harness/$file" >/dev/null
done
docker cp "$MEMORY/hermes_bench/engine.py" "$CONTAINER:$DEST/hermes_bench/engine.py" >/dev/null
docker cp "$MEMORY/harness/questions/fewshot.json" \
  "$CONTAINER:$DEST/harness/questions/fewshot.json" >/dev/null
docker cp "$MEMORY/harness/data/." \
  "$CONTAINER:$DEST/harness/data/" >/dev/null
docker cp "$INTEGRATION/origin/connectors/." \
  "$CONTAINER:$DEST/integration/origin/connectors/" >/dev/null
docker cp "$INTEGRATION/manifests/origin-lock.json" \
  "$CONTAINER:$DEST/integration/manifests/origin-lock.json" >/dev/null
for file in chat.py dialogue.py pipeline.py; do
  docker cp "$INTEGRATION/runtime/$file" "$CONTAINER:$DEST/integration/runtime/$file" >/dev/null
done
docker cp "$INTEGRATION/contexts/ebtl.json" \
  "$CONTAINER:$DEST/integration/contexts/ebtl.json" >/dev/null
docker cp "$INTEGRATION/hermes/workspaces/." \
  "$CONTAINER:/opt/data/work/dss_typed/hermes/workspaces/" >/dev/null

[ "$QUIET" -eq 1 ] || echo "Hermes integration deployed to profile=$PROFILE, workspace=/opt/data/work/dss_typed"
