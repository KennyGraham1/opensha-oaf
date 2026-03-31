#!/usr/bin/env bash
# run_etas_pipeline.sh — Full NZ ETAS pipeline: model → visualisation → pyCSEP tests
#
# Usage:
#   ./run_etas_pipeline.sh                        # uses etas_config.json
#   ./run_etas_pipeline.sh path/to/config.json    # custom config
#   ./run_etas_pipeline.sh --skip-model           # visualisation + tests only (reuse last run)
#   ./run_etas_pipeline.sh --skip-viz             # model only, no visualisation
#   ./run_etas_pipeline.sh --skip-pycsep          # skip pyCSEP tests
#
# Rebuild the jar after any code change with:
#   ./gradlew appNZDemoJar

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JAR="$SCRIPT_DIR/build/libs/ETAS_Demo_NZ.jar"
VIZ_SCRIPT="$SCRIPT_DIR/scripts/python/visualize_nz_etas_output.py"
PYCSEP_SCRIPT="$SCRIPT_DIR/scripts/python/visualize_nz_etas_with_pycsep.py"

# ── Defaults ────────────────────────────────────────────────────────────────
CONFIG="$SCRIPT_DIR/etas_config.json"
SKIP_MODEL=false
SKIP_VIZ=false
SKIP_PYCSEP=false

# Derive a run label from the config filename (strip path and .json extension).
# Used to keep outputs from different experiments in separate directories.
# e.g. etas_config.json → "default"
#      etas_config_premainshock.json → "premainshock"
config_label() {
    local base
    base="$(basename "$1" .json)"
    base="${base#etas_config}"   # strip leading "etas_config"
    base="${base#_}"             # strip leading underscore if present
    echo "${base:-default}"
}

# ── Argument parsing ─────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --skip-model)  SKIP_MODEL=true  ;;
        --skip-viz)    SKIP_VIZ=true    ;;
        --skip-pycsep) SKIP_PYCSEP=true ;;
        *)             CONFIG="$arg"    ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo "[pipeline] $*"; }
fail() { echo "[pipeline] ERROR: $*" >&2; exit 1; }

hr() { echo; echo "──────────────────────────────────────────────────────────"; echo; }

# ── Step 1: Run ETAS model ────────────────────────────────────────────────────
if [ "$SKIP_MODEL" = false ]; then
    hr
    log "Step 1/3 — Running ETAS model"
    log "Config : $CONFIG"
    log "Jar    : $JAR"

    [ -f "$JAR" ]    || fail "Jar not found. Run: ./gradlew appNZDemoJar"
    [ -f "$CONFIG" ] || fail "Config not found: $CONFIG"

    java -jar "$JAR" --config "$CONFIG"
    log "Model run complete."
else
    log "Step 1/3 — Skipping model run (--skip-model)"
fi

# ── Step 2: Visualisation dashboard ──────────────────────────────────────────
if [ "$SKIP_VIZ" = false ]; then
    hr
    log "Step 2/3 — Rendering ensemble dashboard"

    [ -f "$VIZ_SCRIPT" ] || fail "Visualisation script not found: $VIZ_SCRIPT"

    RUN_LABEL="$(config_label "$CONFIG")"
    SUMMARY_FILE="$SCRIPT_DIR/nz_etas_simulations${RUN_LABEL:+_$RUN_LABEL}.txt"
    CATALOG_DIR="$SCRIPT_DIR/simulated_catalogs${RUN_LABEL:+_$RUN_LABEL}"
    SPATIAL_RATE="$SCRIPT_DIR/spatial_rate_map${RUN_LABEL:+_$RUN_LABEL}.csv"
    VIZ_OUT="$SCRIPT_DIR/build/nz_visualization${RUN_LABEL:+_$RUN_LABEL}/nz_etas_dashboard"

    python3 "$VIZ_SCRIPT" \
        --summary      "$SUMMARY_FILE" \
        --catalog-dir  "$CATALOG_DIR" \
        --spatial-rate "$SPATIAL_RATE" \
        --output-stem  "$VIZ_OUT"

    log "Dashboard written to: build/nz_visualization${RUN_LABEL:+_$RUN_LABEL}/"
    ls "$(dirname "$VIZ_OUT")" 2>/dev/null | sed 's/^/    /'
else
    log "Step 2/3 — Skipping visualisation (--skip-viz)"
fi

# ── Step 3: pyCSEP evaluation ─────────────────────────────────────────────────
if [ "$SKIP_PYCSEP" = false ]; then
    hr
    log "Step 3/3 — Running pyCSEP evaluation"

    [ -f "$PYCSEP_SCRIPT" ] || fail "pyCSEP script not found: $PYCSEP_SCRIPT"

    # Check pyCSEP is importable
    if ! python3 -c "import csep" 2>/dev/null; then
        log "pyCSEP not found. Install with:"
        log "  git clone https://github.com/SCECcode/pycsep.git vendor/pycsep"
        log "  python3 -m pip install --user -e vendor/pycsep"
        log "Skipping pyCSEP step."
    else
        RUN_LABEL="$(config_label "$CONFIG")"
        SUMMARY_FILE="$SCRIPT_DIR/nz_etas_simulations${RUN_LABEL:+_$RUN_LABEL}.txt"
        CATALOG_DIR="$SCRIPT_DIR/simulated_catalogs${RUN_LABEL:+_$RUN_LABEL}"
        PYCSEP_OUT="$SCRIPT_DIR/build/pycsep${RUN_LABEL:+_$RUN_LABEL}"

        python3 "$PYCSEP_SCRIPT" \
            --summary     "$SUMMARY_FILE" \
            --config      "$CONFIG" \
            --catalog-dir "$CATALOG_DIR" \
            --output-dir  "$PYCSEP_OUT" \
            --cache-dir   "$PYCSEP_OUT/cache"

        log "pyCSEP outputs written to: build/pycsep${RUN_LABEL:+_$RUN_LABEL}/"
        ls "$PYCSEP_OUT/" 2>/dev/null | sed 's/^/    /'
    fi
else
    log "Step 3/3 — Skipping pyCSEP (--skip-pycsep)"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
hr
log "Pipeline complete."
log "Outputs:"
RUN_LABEL="$(config_label "$CONFIG")"
log "  Config           : $CONFIG"
log "  Forecast summary : nz_etas_simulations${RUN_LABEL:+_$RUN_LABEL}.txt"
log "  Simulated catalogs: simulated_catalogs${RUN_LABEL:+_$RUN_LABEL}/"
[ "$SKIP_VIZ"    = false ] && log "  Dashboard        : build/nz_visualization${RUN_LABEL:+_$RUN_LABEL}/"
[ "$SKIP_PYCSEP" = false ] && log "  pyCSEP plots     : build/pycsep${RUN_LABEL:+_$RUN_LABEL}/"
