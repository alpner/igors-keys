"""
Parser for Cherry KeyM@n "Cherry-Shortcut-FileV2" (.csf) files.

Format (reverse-engineered from CyMotionMasterXPress.csf and Common.csf):
  * MFC CArchive serialization (CObject::Serialize / CRuntimeClass tags).
      - CString: u8 length (0xFF -> u16 length, 0xFFFF -> u32), then bytes (Windows ANSI code page)
      - class tag: u16 0xFFFF, u16 schema, u16 name-length, name   -> new class
                   u16 (0x8000 | n)                                  -> class already seen, index n
        Classes and objects share one index space starting at 1 (MFC m_nMapCount).
  * File = CString "Cherry-Shortcut-FileV2", then one CCSF_Obj containing
    u16 count and `count` shortcut objects, then 10 trailing bytes.
  * Every shortcut object (base class CCherrySC) starts with
      u32 flags      0x80000000 = assignment for the KeyM@n (Fn) layer of the key
                     0x00000400 = seen on two CSystemSC entries (function 0x19/0x1a)
      u32 key        PS/2 set-1 scan code of the physical key (0xE0xx = extended).
                     The Cherry filter driver maps these to HID usages
                     (see driver_hotkey_table.json), e.g. E071 -> consumer 0x0301.
      CString name   display name of the assignment
      u32 a (0), u32 b (1), u8 c (0)   constant in every file seen
    followed by class-specific fields:
      CBrowserSC    u32 function  (1 back, 2 forward, 3 stop, 4 refresh, 7 home)
      CMediaSC      u32 function  (1 next, 2 previous, 3 stop, 4 play/pause), u16 0, u32 20
      CSystemSC     u32 function  (1 CD open, 0x17 scroll up, 0x18 scroll down, 0x19/0x1a ?,
                                   0x1b cut, 0x1c copy, 0x1d paste, 0x1e redo, 0x1f undo), u8 0
      CListSC       u32 function  (2 e-mail, 3 multimedia, 4 browser, 7 XPress list), u16 child count,
                    then that many nested shortcut objects (the programs in the list)
      CExecutableSC CString path, CString parameters, u32 kind (0 program, 3 URL, 7 folder), u32 0
      CPowerSC      u32 function (3), u32 delay_ms, u32 1, u32 1
      CTextMacroSC  u32 function, CString text, u32 0
      CKeyMacroSC   u32 0, u16 count, count x CKeyMacroKey { u32 vkey, u32 flags (0x80000000 = key up) }
"""
import struct, sys, json, os

PS2_NAMES = {  # from the Cherry driver hotkey table + standard PS/2 set 1
    0xE019: "Next Track", 0xE010: "Previous Track", 0xE024: "Media Stop", 0xE022: "Play/Pause", 0xE020: "Mute",
    0xE030: "Volume Up", 0xE02E: "Volume Down", 0xE06D: "Media Select", 0xE06C: "Mail", 0xE021: "Calculator",
    0xE06B: "My Computer", 0xE065: "WWW Search", 0xE032: "WWW Home", 0xE06A: "WWW Back", 0xE069: "WWW Forward",
    0xE068: "WWW Stop", 0xE067: "WWW Refresh", 0xE066: "WWW Favorites", 0xE05F: "Sleep", 0xE063: "WakeUp",
    0xE012: "XPress key 2 (Scroll Down)", 0xE00B: "XPress key 1 (Scroll Up)", 0xE017: "XPress key 3 (Cut)",
    0xE00A: "XPress key 4 (Paste)", 0xE018: "XPress key 5 (Copy)", 0xE071: "XPress key 6 (XPress1)",
    0xE02C: "XPress key 7 (XPress2)", 0xE072: "XPress key 8 (XPress3)", 0xE007: "XPress key 9 (Redo)",
    0xE008: "XPress key 10 (Undo)", 0xE070: "CD Open", 0xE00E: "KeyM@n (Fn) key",
    0x45: "Num Lock", 0x46: "Scroll Lock", 0x3A: "Caps Lock", 0x53: "Keypad . Del",
}
BROWSER_FN = {1: "back", 2: "forward", 3: "stop", 4: "refresh", 7: "home"}
MEDIA_FN = {1: "next track", 2: "previous track", 3: "stop", 4: "play/pause"}
SYSTEM_FN = {1: "CD open/eject", 0x17: "scroll up", 0x18: "scroll down", 0x19: "(0x19, unknown)", 0x1a: "(0x1a, unknown)",
             0x1b: "cut", 0x1c: "copy", 0x1d: "paste", 0x1e: "redo", 0x1f: "undo"}
LIST_FN = {2: "e-mail program list", 3: "multimedia program list", 4: "browser program list", 7: "XPress list"}
EXEC_KIND = {0: "program", 3: "internet address", 7: "folder"}


class Reader:
    def __init__(self, data):
        self.b = data
        self.p = 0

    def u8(self):
        v = self.b[self.p]; self.p += 1; return v

    def u16(self):
        v = struct.unpack_from('<H', self.b, self.p)[0]; self.p += 2; return v

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.p)[0]; self.p += 4; return v

    def cstring(self):
        n = self.u8()
        if n == 0xFF:
            n = self.u16()
            if n == 0xFFFF:
                n = self.u32()
        s = self.b[self.p:self.p + n]; self.p += n
        # KeyM@n wrote the Windows ANSI code page of the machine (cp1250 in Slovenia, cp1252 in Western Europe);
        # 'mbcs' is that code page on the machine doing the import, which is almost always the same one.
        return s.decode('mbcs', 'replace')


def parse(data):
    r = Reader(data)
    magic = r.cstring()
    if magic != 'Cherry-Shortcut-FileV2':
        raise ValueError('not a Cherry-Shortcut-FileV2: %r' % magic)
    classes = {}
    state = {'n': 1}

    def read_class():
        tag = r.u16()
        if tag == 0xFFFF:
            schema = r.u16(); n = r.u16()
            name = r.b[r.p:r.p + n].decode('ascii'); r.p += n
            classes[state['n']] = name; state['n'] += 1
        elif tag & 0x8000 and (tag & 0x7FFF) in classes:
            name = classes[tag & 0x7FFF]
        else:
            raise ValueError('unexpected class tag %#x at offset %#x' % (tag, r.p - 2))
        state['n'] += 1  # the object itself takes an index too
        return name

    root = read_class()
    if root != 'CCSF_Obj':
        raise ValueError('unexpected root class %s' % root)
    def read_object():
        cls = read_class()
        o = {'class': cls, 'flags': r.u32(), 'key': r.u32()}
        o['key_hex'] = '%04X' % o['key']
        o['key_name'] = PS2_NAMES.get(o['key'], '?')
        o['keyman_layer'] = bool(o['flags'] & 0x80000000)
        o['name'] = r.cstring()
        o['_a'], o['_b'], o['_c'] = r.u32(), r.u32(), r.u8()
        if cls == 'CBrowserSC':
            o['function'] = r.u32(); o['action'] = 'browser ' + BROWSER_FN.get(o['function'], str(o['function']))
        elif cls == 'CMediaSC':
            o['function'] = r.u32(); o['_d'] = r.u16(); o['_e'] = r.u32()
            o['action'] = 'media ' + MEDIA_FN.get(o['function'], str(o['function']))
        elif cls == 'CSystemSC':
            o['function'] = r.u32(); o['_d'] = r.u8()
            o['action'] = 'system ' + SYSTEM_FN.get(o['function'], str(o['function']))
        elif cls == 'CListSC':
            o['function'] = r.u32(); nchild = r.u16()
            o['action'] = 'list ' + LIST_FN.get(o['function'], str(o['function']))
            o['children'] = [read_object() for _ in range(nchild)]
        elif cls == 'CExecutableSC':
            o['path'] = r.cstring(); o['parameters'] = r.cstring(); o['kind'] = r.u32(); o['_d'] = r.u32()
            o['action'] = 'open %s: %s %s' % (EXEC_KIND.get(o['kind'], o['kind']), o['path'], o['parameters'])
        elif cls == 'CPowerSC':
            o['function'] = r.u32(); o['delay_ms'] = r.u32(); o['_d'] = r.u32(); o['_e'] = r.u32()
            o['action'] = 'power function %d after %d ms' % (o['function'], o['delay_ms'])
        elif cls == 'CTextMacroSC':
            o['function'] = r.u32(); o['text'] = r.cstring(); o['_d'] = r.u32()
            o['action'] = 'type text %r' % o['text']
        elif cls == 'CKeyMacroSC':
            o['_d'] = r.u32(); n = r.u16(); keys = []
            for _ in range(n):
                kc = read_class()
                vk = r.u32(); fl = r.u32()
                keys.append({'vkey': vk, 'vkey_hex': '%02X' % vk, 'up': bool(fl & 0x80000000)})
            o['macro'] = keys
            o['action'] = 'key macro ' + ' '.join(('%s%02X' % ('-' if k['up'] else '+', k['vkey'])) for k in keys)
        else:
            raise ValueError('unknown shortcut class %s at %#x' % (cls, r.p))
        return o

    count = r.u16()
    objs = [read_object() for _ in range(count)]
    trailer = r.b[r.p:]
    return {'magic': magic, 'count': count, 'objects': objs, 'trailer_hex': trailer.hex(), 'consumed': r.p, 'size': len(data)}


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'CyMotionMasterXPress.csf')
    res = parse(open(path, 'rb').read())
    print('%s: %d objects, consumed %d of %d bytes, trailer %s' % (path, res['count'], res['consumed'], res['size'], res['trailer_hex']))
    print('%-5s %-4s %-28s %-14s %-20s %s' % ('key', 'fn?', 'physical key', 'class', 'name', 'action'))
    def show(o, indent=0):
        print('%s%-5s %-4s %-28s %-14s %-20s %s' % ('  ' * indent, o['key_hex'], 'Fn' if o['keyman_layer'] else '',
                                                    o['key_name'][:28], o['class'], o['name'][:20], o['action']))
        for ch in o.get('children', []):
            show(ch, indent + 1)
    for o in res['objects']:
        show(o)
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
