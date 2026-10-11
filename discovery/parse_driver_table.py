"""Extract the PS/2-scancode -> HID-usage hotkey table from Cherry's Ch64USB.sys filter driver.
Entries are 32 bytes: [8 bytes model bitmask][u16 hid usage][u16 kind][u32 =1][u64 ps2 scan][u64 name RVA]"""
import struct, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
b = open(os.path.join(HERE, '..', 'CDI', 'Driver', 'Win7', 'x64', 'ch64usb.sys'), 'rb').read()

# PE section table for RVA -> file offset
pe = struct.unpack_from('<I', b, 0x3c)[0]
nsec = struct.unpack_from('<H', b, pe + 6)[0]
opt_size = struct.unpack_from('<H', b, pe + 20)[0]
secs = []
for i in range(nsec):
    off = pe + 24 + opt_size + i * 40
    name = b[off:off+8].rstrip(b'\0').decode()
    vsize, va, rsize, raw = struct.unpack_from('<IIII', b, off + 8)
    secs.append((name, va, vsize, raw, rsize))
def rva2off(rva):
    for name, va, vsize, raw, rsize in secs:
        if va <= rva < va + max(vsize, rsize):
            return raw + (rva - va)
    return None
def cstr(off):
    if off is None: return None
    e = b.index(b'\0', off)
    try: return b[off:e].decode('ascii')
    except: return b[off:e].hex()
def wstr(off):
    if off is None: return None
    e = b.index(b'\0\0', off)
    e += e % 2
    try: return b[off:e].decode('utf-16le')
    except: return None

def entry(off):
    mask, usage, kind, one, ps2, nameptr = struct.unpack_from('<QHHIQQ', b, off)
    return dict(off=off, mask=mask, usage=usage, kind=kind, one=one, ps2=ps2, nameptr=nameptr)

def valid(e):
    return e['one'] == 1 and e['ps2'] < 0x10000 and 0x1000 < e['nameptr'] < 0x100000 and e['usage'] < 0x1000

# find all contiguous runs of valid entries
runs = []
off = 0
while off + 32 <= len(b):
    e = entry(off)
    if valid(e):
        start = off
        while off + 32 <= len(b) and valid(entry(off)):
            off += 32
        if (off - start) // 32 >= 4:
            runs.append((start, off))
    else:
        off += 8
table = []
for start, end in runs:
    for o in range(start, end, 32):
        e = entry(o)
        noff = rva2off(e['nameptr'])
        e['name'] = cstr(noff)
        if e['name'] is not None and not e['name'].isprintable():
            e['name'] = wstr(noff)
        table.append(e)
print(f"found {len(runs)} table run(s): {[(hex(s),hex(e),(e-s)//32) for s,e in runs]}")
print(f"{'file off':<9}{'ps2':<8}{'usage':<8}{'kind':<6}{'mask':<20}name")
for e in table:
    print(f"{e['off']:<9x}{e['ps2']:<8x}{e['usage']:<8x}{e['kind']:<6}{e['mask']:<20x}{e['name']}")
# valid() keeps only the hotkey rows this keyboard family adds; the JSON carries just the facts needed to translate
# a KeyM@n .csf file (PS/2 scan code -> HID usage -> name), not offsets or pointers into the driver.
json.dump([{'ps2': hex(e['ps2']), 'usage': hex(e['usage']), 'name': e['name']} for e in table],
          open(os.path.join(HERE, 'driver_hotkey_table.json'), 'w'), indent=2)
