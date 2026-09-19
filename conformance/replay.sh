#!/usr/bin/env bash
# Portable conformance replayer in shell: curl + jq only, zero Python/Node.
# Replays the SAME conformance/fixtures/*.json as replay.py — dependency-free
# verification for minimal environments. CI runs it; humans run it to prove
# a port with nothing but the base system.
#
# Usage: ./conformance/replay.sh <base_url> [fixture-file ...]
#   Example: ./conformance/replay.sh http://127.0.0.1:8496
# Requires bash 4+ (any Linux; macOS ships bash 3 — `brew install bash`),
# curl, and jq. Run from the repo root.
#
# Matcher parity with replay.py: status, has, absent, where (dotted paths
# with numeric indices), headers, identical_to, capture, save_as, {var}
# substitution. Exit 1 on any failure.
set -u
BASE="${1:?usage: replay.sh <base_url> [fixture ...]}"
shift
if [ "$#" -eq 0 ]; then
  set -- conformance/fixtures/*.json
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

# dotted.path.0.here -> jq expression (.["dotted"]["path"][0]["here"])
tojq() {
  local out="." seg first=1
  IFS='.' read -ra SEGS <<< "$1"
  for seg in "${SEGS[@]}"; do
    if [[ "$seg" =~ ^[0-9]+$ ]]; then
      out="${out}[${seg}]"
    else
      out="${out}[\"${seg}\"]"
    fi
  done
  printf '%s' "$out"
}

fail() { echo "  FAIL $1: $2"; FAIL=$((FAIL + 1)); }
pass() { echo "  PASS $1"; PASS=$((PASS + 1)); }

for FILE in "$@"; do
  echo "[$FILE]"
  VER="$(jq -r '.version' "$FILE")"
  if [ "$VER" != "0.1" ]; then echo "  FAIL unsupported version $VER"; FAIL=$((FAIL + 1)); continue; fi
  declare -A VARS=()
  declare -A SAVED=()
  N="$(jq '.fixtures | length' "$FILE")"
  for ((i = 0; i < N; i++)); do
    FX="$TMP/fx.json"
    jq -c ".fixtures[$i]" "$FILE" > "$FX"
    NAME="$(jq -r '.name' "$FX")"
    METHOD="$(jq -r '.request.method' "$FX")"
    P="$(jq -r '.request.path' "$FX")"
    # substitute {vars} in path, headers, body (known vars only)
    for k in "${!VARS[@]}"; do P="${P//\{$k\}/${VARS[$k]}}"; done
    ARGS=(-s -o "$TMP/body.json" -D "$TMP/hdrs.txt" -w "%{http_code}" -X "$METHOD")
    ARGS+=(-H "Content-Type: application/json")
    HDRS="$(jq -c '.request.headers // {}' "$FX")"
    while IFS=$'\t' read -r hk hv; do
      [ "$hk" = "_" ] && continue
      for k in "${!VARS[@]}"; do hv="${hv//\{$k\}/${VARS[$k]}}"; done
      ARGS+=(-H "$hk: $hv")
    done < <(echo "$HDRS" | jq -r 'to_entries[] | "\(.key)\t\(.value)"' | sed 's/^{}$/_	_/')
    if jq -e '.request | has("body")' "$FX" > /dev/null; then
      BODY="$(jq -c '.request.body' "$FX")"
      for k in "${!VARS[@]}"; do BODY="${BODY//\{$k\}/${VARS[$k]}}"; done
      ARGS+=(--data "$BODY")
    fi
    STATUS="$(curl "${ARGS[@]}" "$BASE$P")"
    F=""
    EXP_STATUS="$(jq -r '.expect.status // empty' "$FX")"
    [ -n "$EXP_STATUS" ] && [ "$STATUS" != "$EXP_STATUS" ] && \
      F="${F}status $STATUS != $EXP_STATUS ($(head -c 200 "$TMP/body.json")); "
    while IFS= read -r hk; do
      jq -e --arg k "$hk" 'has($k)' "$TMP/body.json" > /dev/null || F="${F}missing key $hk; "
    done < <(jq -r '.expect.has // [] | .[]' "$FX")
    while IFS= read -r ap; do
      [ -z "$ap" ] && continue
      GOT="$(jq -c "$(tojq "$ap") // \"__AMCP_ABSENT__\"" "$TMP/body.json")"
      [ "$GOT" != '"__AMCP_ABSENT__"' ] && F="${F}forbidden path present: $ap; "
    done < <(jq -r '.expect.absent // [] | .[]' "$FX")
    while IFS= read -r wkey; do
      [ -z "$wkey" ] && continue
      WANT="$(jq -S -c --arg k "$wkey" '.expect.where[$k]' "$FX")"
      for k in "${!VARS[@]}"; do WANT="${WANT//\{$k\}/${VARS[$k]}}"; done
      GOT="$(jq -S -c "$(tojq "$wkey")" "$TMP/body.json")"
      [ "$GOT" != "$WANT" ] && F="${F}$wkey: $GOT != $WANT; "
    done < <(jq -r '.expect.where // {} | keys[]' "$FX")
    while IFS=$'\t' read -r hk hv; do
      [ "$hk" = "_" ] && continue
      ACTUAL="$(grep -i "^$hk:" "$TMP/hdrs.txt" | head -1 | sed 's/^[^:]*:[[:space:]]*//;s/\r$//')"
      [ "$ACTUAL" != "$hv" ] && F="${F}header $hk: $ACTUAL != $hv; "
    done < <(jq -r '.expect.headers // {} | to_entries[] | "\(.key)\t\(.value)"' | sed 's/^{}$/_	_/')
    IDENT="$(jq -r '.expect.identical_to // empty' "$FX")"
    if [ -n "$IDENT" ]; then
      A="$(jq -S -c . "$TMP/body.json")"; B="$(jq -S -c . "$TMP/save_$IDENT")"
      [ "$A" != "$B" ] && F="${F}body differs from saved $IDENT; "
    fi
    while IFS=$'\t' read -r vk vp; do
      [ "$vk" = "_" ] && continue
      VAL="$(jq -c "$(tojq "$vp")" "$TMP/body.json")"
      if [ "$VAL" = "null" ]; then F="${F}capture failed: $vp; "
      else VARS[$vk]="$(echo "$VAL" | jq -r 'if type=="string" then . else tojson end')"; fi
    done < <(jq -r '.capture // {} | to_entries[] | "\(.key)\t\(.value)"' | sed 's/^{}$/_	_/')
    SAVE="$(jq -r '.save_as // empty' "$FX")"
    [ -n "$SAVE" ] && cp "$TMP/body.json" "$TMP/save_$SAVE"
    if [ -z "$F" ]; then pass "$NAME"; else fail "$NAME" "$F"; fi
  done
done

echo ""
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
