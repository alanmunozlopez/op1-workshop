#!/usr/bin/env python3
"""Verify/extract the official SDK snapshot already included in this fork."""
from pathlib import Path
import hashlib
import tarfile

ROOT = Path(__file__).resolve().parents[2]
VERSION = '3.2.3'
PIN = '7a74872170bcb812750b65989184ef81fd06ab1fbb6c9066091a613162137033'
ARCHIVE = ROOT / f'source/hundekraft-{VERSION}-source.tar.gz'
DESTINATION = ROOT / '.work/sdk'
SDK = DESTINATION / f'hundekraft-{VERSION}-source/ext/kennel'


def prepare():
    declared = Path(str(ARCHIVE)+'.sha256').read_text().split()[0]
    actual = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    if declared != PIN or actual != PIN:
        raise SystemExit('REFUSED: SDK archive/checksum differs from the audited 3.2.3 snapshot')
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with tarfile.open(ARCHIVE) as bundle:
        for member in bundle.getmembers():
            target = (DESTINATION/member.name).resolve()
            if DESTINATION.resolve() not in target.parents or not (member.isfile() or member.isdir()):
                raise SystemExit('REFUSED: unsafe archive member '+member.name)
        if not SDK.is_dir():
            bundle.extractall(DESTINATION, filter='data')
        # Detect local edits in the build inputs and the services audited below.
        for relative in ('synth_sdk/op1_plugin.h', 'synth_sdk/op1_feature.h',
                         'synth_sdk/kennel/kn_exports.c', 'synth_sdk/kennel/kn_core.c',
                         'synth_sdk/kennel/kn_midi.c', 'tools/kennel/pack.py'):
            name=f'hundekraft-{VERSION}-source/ext/kennel/{relative}'
            expected=bundle.extractfile(name).read()
            if (SDK/relative).read_bytes() != expected:
                raise SystemExit('REFUSED: extracted SDK was edited: '+relative)
    return SDK


if __name__ == '__main__':
    print(prepare())
