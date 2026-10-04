#!/bin/sh
# Single finalizer for alignment passes: runs the three measurement commands in
# order and stops at the first failure. A pass that skips one of the three can
# read as clean while being unmeasured.
#
# Usage: sh scripts/align_check.sh [TARGET_DIR]
# Deps: python3 only. Must be run from the skill root.
set -e
TARGET="${1:-.}"
echo "1/3 validate_skill.py"
python3 scripts/validate_skill.py "$TARGET"
echo "2/3 grade_evals.py"
python3 scripts/grade_evals.py
echo "3/3 eval_diagnostics.py"
python3 scripts/eval_diagnostics.py
echo "align_check: all three measurements completed"
