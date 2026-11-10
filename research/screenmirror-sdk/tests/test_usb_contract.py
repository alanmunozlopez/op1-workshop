#!/usr/bin/env python3
"""Read-only, pinned SDK3.2.3 USB-MIDI contract check; never opens MIDI.

Extracts the actual two C function bodies from the verified public SDK, mocks
only TX_ENQ and the raw feature observer, and compiles in a deleted temporary
folder. The SDK bodies retain their original semantics; no firmware pointers are
called. GPL-3.0-or-later with the OP-1 permission for the extracted SDK code; see
its LICENSE and NOTICE. Host expectations are synthetic, not hardware evidence.
"""
from pathlib import Path
import argparse
import hashlib
import subprocess
import tempfile

PINS = {
    'synth_sdk/kennel/kn_core.c': '98330dddad6cebe943a85dae23133e3cb5b8133cf33db8e3774e1c3064d993db',
    'synth_sdk/kennel/kn_midi.c': '6ea58e9507b469dd09ae7d2f72731446bc7051fa2bb41a23912f58551c920c60',
}
PREFIX = r'''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
static unsigned sends,received,last_word,usb_clocks;
#define KN_RX_POSTED 0xF0u
static void tx_mock(int cable,const void *p,unsigned count) {
    assert(cable==0 && count==1);last_word=*(const uint32_t*)p;sends++;
}
#define TX_ENQ tx_mock
static void kn_midi_raw(const uint8_t *p,int n) {
    (void)p;assert(n==3);received++;
}
'''
TESTS = r'''
int main(void) {
    uint8_t note[]={0x90,60,100},start[]={0xF0,0x7D,0x53};
    uint8_t more[]={0x4D,5,0},end[]={0xF7},whole[92]={0xF0};
    whole[1]=0x7D;whole[91]=0xF7; /* valid bounded seven-bit SysEx framing */
    assert(op1_midi_send(note,3)==0 && (last_word&15)==9);
    assert(op1_midi_send(start,3)==0 && (last_word&15)==3);
    /* USB-MIDI SysEx start/continuation would require CIN4, not CIN3. */
    unsigned old=sends;
    assert(op1_midi_send(more,3)==-1 && sends==old);
    assert(op1_midi_send(whole,92)==-1 && sends==old);
    assert(op1_midi_send(end,1)==0 && (last_word&15)==5);
    uint8_t pk_note[]={9,0x90,60,100};
    uint8_t pk_sysex[]={4,0xF0,0x7D,0x53},pk_end[]={5,0xF7,0,0};
    kn_midi_raw_packet(pk_note);assert(received==1);
    kn_midi_raw_packet(pk_sysex);kn_midi_raw_packet(pk_end);
    assert(received==1);
    puts("PASS SDK3.2.3 actual C: short MIDI accepted; full SysEx rejected; F0 encoded as CIN3; data continuation rejected; SysEx RX not exposed");
    return 0;
}
'''


def extract(source, signature):
    start = source.index(signature)
    end = source.index('\n}', start) + 2
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True, help='ext/kennel directory from verified3.2.3 archive')
    parser.add_argument('--cc', default='cc', help='host C compiler, never Blackfin')
    args = parser.parse_args()
    source = {}
    for relative, digest in PINS.items():
        blob = (args.sdk/relative).read_bytes()
        if hashlib.sha256(blob).hexdigest() != digest:
            raise SystemExit('REFUSED: SDK source changed; re-audit '+relative)
        source[relative] = blob.decode()
    code = PREFIX + extract(source['synth_sdk/kennel/kn_core.c'], 'int op1_midi_send(')
    code += '\n' + extract(source['synth_sdk/kennel/kn_midi.c'], 'void kn_midi_raw_packet(') + TESTS
    with tempfile.TemporaryDirectory(prefix='hundekraft-usb-audit-') as directory:
        folder = Path(directory); c = folder/'contract.c';binary=folder/'contract'
        c.write_text(code)
        subprocess.run([args.cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic',
                        '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                        str(c),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)
    print('PASS: deleted temporary build; no MIDI/audio/device access occurred')


if __name__ == '__main__':
    main()
