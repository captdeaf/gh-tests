#!/bin/env python3

import re
import sys
import json

def Key(qmkid, label, tooltip=None, **args):
    d = dict(qmkid=qmkid, str=label, **args)
    if tooltip is not None:
        d['title'] = tooltip
    return d

def parse_quantum_keycodes(inpath):
    with open(inpath, 'r', encoding='utf-8') as fin:
        lines = fin.readlines()

    haseq = re.compile(r'=')
    ispp = re.compile(r'#')
    lines = [x for x in lines if re.search(haseq, x)]
    lines = [x for x in lines if not re.match(ispp, x)]

    keymap = dict()
    codemap = dict()
    aliases = dict()

    matcher = re.compile(r'(\w+)\s*=\s*(\w+)')
    for line in lines:
        m = re.search(matcher, line)
        qmkid = m[1]
        if m[2].startswith('0x'):
            code = int(m[2], 16)
            codemap[code] = qmkid
            keymap[qmkid] = Key(qmkid, qmkid, qmkid, code=code)
            aliases[qmkid] = qmkid
        else:
            # aliases.
            aliases[qmkid] = m[2]

    print(f"QMK: Found {len(keymap)} keycodes.h")

    return (codemap, keymap, aliases)

def parse_vial_keys(inpath):
    vialkeys = dict()

    def K(qmkid, *args, **kwargs):
        d = Key(qmkid, *args, **kwargs)
        vialkeys[qmkid] = d

    with open(inpath, 'r', encoding='utf-8') as fin:
        lines = fin.readlines()

    lines = [x.strip().strip(',') for x in lines]
    lines = [x for x in lines if x.startswith('K(')]

    for line in lines:
        try:
            eval(line)
        except SyntaxError:
            pass

    print(f"Found {len(vialkeys)} descs in vial's keycodes.py")
    return vialkeys

def main():
    if len(sys.argv) != 3:
        print("qmk's keycodes.h path needed.")
        print("vial-gui's keycodes.py path needed.")
        print("You probably want:")
        print(f"{sys.argv[0]} ../vial-qmk/quantum/keycodes.h ../vial-gui/src/main/python/keycodes/keycodes.py")
        return
    qmkpath = sys.argv[1]
    vialpath = sys.argv[2]

    codemap, keymap, aliases = parse_quantum_keycodes(qmkpath)
    vialkeys = parse_vial_keys(vialpath)

    dumbaliases = dict()
    for alias, qmkid in aliases.items():
        dumbaliases[alias.replace('_', '')] = qmkid

    # We have our basics from qmk. Let's also import python's.
    from keycodes_v6 import keycodes_v6 as kc6

    # Update our aliases for vial's dumb versions.
    # We map code to qmkid.
    for pyid, code in kc6.kc.items():
        if pyid not in aliases:
            if code in codemap:
                aliases[pyid] = codemap[code]
                continue
        aliases[pyid] = pyid
        codemap[code] = pyid
        keymap[pyid] = Key(pyid, pyid, pyid, code=code)

    print("Okay, merge:")

    from custom_keys import custom_keys, custom_codes, custom_aliases

    aliases.update(custom_aliases)

    # Vial's keycodes from vial-gui/src/main/python/keycodes/keycodes.py
    for qmkid, desc in vialkeys.items():
        print(f"Looking for {qmkid}")
        # We may get an alias.
        qmkid = aliases[qmkid]
        if qmkid in keymap:
            keymap[qmkid].update(desc)
        else:
            print(f"WARNING: qmkid {qmkid} has no code")
            keymap[qmkid] = desc

    # Imprint custom keys.
    for qmkid, key in custom_keys.items():
        keymap[qmkid].update(key)

    for qmkid, code in custom_codes.items():
        codemap[code] = qmkid

    print(f"Got {len(keymap)} keys and {len(codemap)} codes")

    codemapjs = json.dumps(codemap, indent=2)
    keymapjs = json.dumps(keymap, indent=2)

    def hexify(m):
        return f": 0x{int(m[1], 10):04x},"

    codemapjs = re.sub(': (\\d+),', hexify, codemapjs)
    keymapjs = re.sub(': (\\d+),', hexify, keymapjs)

    with open('pages/js/keygen.js', 'w', encoding='utf-8') as fout:
        fout.write("/////////////////////////////////\n")
        fout.write("/////////////////////////////////\n")
        fout.write("// THIS FILE IS AUTOGENERATED!\n")
        fout.write("/////////////////////////////////\n")
        fout.write("/////////////////////////////////\n")

        fout.write('const CODEMAP = ')
        fout.write(codemapjs)
        fout.write(';\n')
        fout.write('\n')
        fout.write('const KEYMAP = ')
        fout.write(keymapjs)
        fout.write(';\n')

if __name__ == "__main__":
    main()
