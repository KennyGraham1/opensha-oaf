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

    python3 "$VIZ_SCRIPT" \
        --summary   "$SCRIPT_DIR/nz_etas_simulations.txt" \
        --catalogs  "$SCRIPT_DIR/simulated_catalogs" \
        --output    "$SCRIPT_DIR/build/nz_visualization"

    log "Dashboard written to: build/nz_visualization/"
    ls "$SCRIPT_DIR/build/nz_visualization/" 2>/dev/null | sed 's/^/    /'
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
        python3 "$PYCSEP_SCRIPT" \
            --catalogs "$SCRIPT_DIR/simulated_catalogs" \
            --output   "$SCRIPT_DIR/build/pycsep"

        log "pyCSEP outputs written to: build/pycsep/"
        ls "$SCRIPT_DIR/build/pycsep/" 2>/dev/null | sed 's/^/    /'
    fi
else
    log "Step 3/3 — Skipping pyCSEP (--skip-pycsep)"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
hr
log "Pipeline complete."
log "Outputs:"
log "  Forecast summary : nz_etas_simulations.txt"
log "  Simulated catalogs: simulated_catalogs/"
[ "$SKIP_VIZ"    = false ] && log "  Dashboard        : build/nz_visualization/"
[ "$SKIP_PYCSEP" = false ] && log "  pyCSEP plots     : build/pycsep/"
