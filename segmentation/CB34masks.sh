#!/bin/bash
# ============================================================================
# CB3.sh — Cellpose batch segmentation for Fig.2_Microstructures
#   HIPE paper Fig.2  |  Droplet connectivity (C = 2M/N)
#
# Revised 2026-06-22 — based on methods_workflow.md §4 + pipeline_runbook.md
#
# Key changes from upstream CB3.sh:
#   1. Hardcoded /home/yang/... path -> parameterized via $1 or $BASE_DIR
#   2. CRITICAL: --save_rois  ->  --save_tif --save_masks
#      Rationale: ROI rasterization has 0-2 px jaggies (Cellpose ROIs use
#      imageJ ROI format, not pixel-aligned). RAG 8-adjacency misses real
#      contacts -> C = 2M/N underestimated. Direct mask output is
#      pixel-perfect and the only path that matches the runbook.
#   3. flow_threshold 3.0 -> 0.4 (Cellpose default).
#      HIPE droplets are well-separated bright objects; 3.0 is at the
#      upper bound and discards too many true positives.
#   4. Generic traversal: iterate all direct subdirs of BASE_DIR
#      (not a hardcoded 4-stabilizer list). Server-side data is uploaded
#      to /data/lyon/Cellpose260622/ with whatever subdir structure
#      the user provides — typically BSA/GA/SDS/Misco, but flexible.
#      PATTERN env var allows selective subdir matching.
#   5. Filter out underscore-prefixed dirs (_logs) and dotfiles.
#   6. set -euo pipefail, log to _logs/, skip dirs that don't exist.
#
# Usage:
#   ./CB3.sh                                        # default (server path)
#   ./CB3.sh /path/to/Fig.2_Microstructures         # explicit
#   BASE_DIR=/data/lyon/Cellpose260622 ./CB3.sh     # override via env
#   PATTERN='BSA*' ./CB3.sh                         # only BSA-prefixed
#
# Env overrides:
#   MODEL=cyto3          (Cellpose model name)
#   DIAMETER=0           (0 = auto-estimate; HIPE scales vary, keep auto)
#   FLOW_THRESHOLD=0.4   (Cellpose default; raise if oversegmented)
#   PATTERN='*/'         (glob for subdir selection; default = all)
#
# Output:
#   <BASE_DIR>/<STAB>/<sub-condition>/*_masks.tif  (16/32-bit label mask)
#   <BASE_DIR>/_logs/cellpose_<timestamp>.log
#
# Next step (see pipeline_runbook.md step 3):
#   Load *_masks.tif into Fiji, run morpholibj_centroid_rag.ijm
# ============================================================================

set -euo pipefail

# ---- Config ----------------------------------------------------------------
# Server-side default: data is uploaded to /data/lyon/Cellpose260622/.
# Override with $1, $BASE_DIR, or symlink — script is otherwise
# data-structure-agnostic (iterates all direct subdirs of BASE_DIR).
BASE_DIR="${1:-${BASE_DIR:-/data/lyon/Cellpose260622}}"
MODEL="${MODEL:-cyto3}"
DIAMETER="${DIAMETER:-0}"
FLOW_THRESHOLD="${FLOW_THRESHOLD:-0.4}"
PATTERN="${PATTERN:-*/}"   # glob for subdir selection; default = all

# Forward-slash normalize (bash on Windows handles both, but log/grep safer)
BASE_DIR="${BASE_DIR//\\//}"

# ---- Logging ---------------------------------------------------------------
LOG_DIR="${BASE_DIR}/_logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/cellpose_$(date +%Y%m%d_%H%M%S).log"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

# ---- Preflight -------------------------------------------------------------
if [ ! -d "$BASE_DIR" ]; then
    log "ERROR: BASE_DIR does not exist: $BASE_DIR"
    exit 1
fi

if ! command -v python >/dev/null 2>&1; then
    log "ERROR: python not found in PATH"
    exit 1
fi

log "Cellpose batch start"
log "  BASE_DIR      = $BASE_DIR"
log "  MODEL         = $MODEL"
log "  DIAMETER      = $DIAMETER"
log "  FLOW_THRESHOLD= $FLOW_THRESHOLD"
log "  LOG_FILE      = $LOG_FILE"

# ---- Main loop: traverse direct subdirs of BASE_DIR ------------------------
# - PATTERN glob (default '*/') controls which subdirs to process
# - Skip underscore-prefixed dirs (e.g. _logs/) and dotfiles
# - Cellpose --dir is itself recursive, so sub-conditions inside each
#   subdir (e.g. BSA/0.5mM_BSA_F0.68/*.tif) are picked up automatically
shopt -s nullglob
matches=( "${BASE_DIR}"/${PATTERN} )
shopt -u nullglob

if [ "${#matches[@]}" -eq 0 ]; then
    log "ERROR: no subdirs match PATTERN='${PATTERN}' under ${BASE_DIR}"
    exit 1
fi

log "Found ${#matches[@]} subdir(s) to process"

# Track per-subdir results for final summary
SUCCEEDED_DIRS=()
FAILED_DIRS=()

for subdir in "${matches[@]}"; do
    # Only directories, skip hidden / underscore-prefixed (e.g. _logs)
    [ -d "$subdir" ] || continue
    name="$(basename "$subdir")"
    case "$name" in
        _*|.*) continue ;;
    esac

    log "=========================================="
    log "Processing: ${subdir}"
    log "=========================================="

    if ! python -m cellpose \
            --dir "${subdir}" \
            --pretrained_model "${MODEL}" \
            --diameter "${DIAMETER}" \
            --flow_threshold "${FLOW_THRESHOLD}" \
            --save_tif \
            --use_gpu \
            --verbose 2>&1 | tee -a "${LOG_FILE}"; then
        FAILED_DIRS+=("${subdir}")
        log "ERROR: Cellpose failed on ${subdir}"
        log "       Continuing with next subdir (set -e to abort batch)"
    else
        SUCCEEDED_DIRS+=("${subdir}")
    fi

    log "Done: ${subdir}"
done

# ---- Final summary ---------------------------------------------------------
log "=========================================="
log "Cellpose batch finished"
log "  Succeeded: ${#SUCCEEDED_DIRS[@]} / $(( ${#SUCCEEDED_DIRS[@]} + ${#FAILED_DIRS[@]} ))"
log "  Failed:    ${#FAILED_DIRS[@]}"
if [ "${#FAILED_DIRS[@]}" -gt 0 ]; then
    log "  Failed subdirs:"
    for d in "${FAILED_DIRS[@]}"; do
        log "    - $d"
    done
fi

log "Cellpose batch complete"
log "Next: verify outputs and run morpholibj_centroid_rag.ijm (see pipeline_runbook.md step 3)"
