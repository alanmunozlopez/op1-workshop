#!/bin/sh
# Local compiler/packer check. Never connects to MIDI or the OP-1.
set -eu
task_audit_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
task_sdk=$(python3 "$task_audit_dir/bootstrap_sdk.py")
if [ -n "${BFIN_BIN:-}" ]; then
    PATH="$BFIN_BIN:$PATH"
    export PATH
fi
command -v bfin-elf-gcc >/dev/null
command -v bfin-elf-ld >/dev/null
mkdir -p "$task_audit_dir/artifacts" "$task_audit_dir/../../.work/probe-objects"
python3 "$task_sdk/tools/kennel/pack.py" \
    "$task_audit_dir/probe/sm_sdk_probe" \
    -o "$task_audit_dir/artifacts/sm_sdk_probe.knl" \
    --keep "$task_audit_dir/../../.work/probe-objects"
python3 "$task_audit_dir/tests/test_usb_contract.py" --sdk "$task_sdk"
