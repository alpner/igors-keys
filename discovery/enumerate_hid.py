"""Enumerate every HID top-level collection of the Cherry keyboard (VID 046A)
and dump attributes + report descriptor (reconstructed by hidapi from Windows
preparsed data) to discovery/hid_enumeration.json and .txt."""
import hid, json, sys, os

VID = 0x046A
out_dir = os.path.dirname(os.path.abspath(__file__))

def decode_descriptor(data):
    """Minimal HID report-descriptor disassembler (short items only)."""
    names = {
        0x04: "Usage Page", 0x08: "Usage", 0x14: "Logical Minimum", 0x24: "Logical Maximum",
        0x34: "Physical Minimum", 0x44: "Physical Maximum", 0x54: "Unit Exponent", 0x64: "Unit",
        0x74: "Report Size", 0x80: "Input", 0x84: "Report ID", 0x90: "Output", 0x94: "Report Count",
        0xA0: "Collection", 0xA4: "Push", 0xB0: "Feature", 0xB4: "Pop", 0xC0: "End Collection",
        0x18: "Usage Minimum", 0x28: "Usage Maximum", 0x38: "Designator Index",
        0x48: "Designator Minimum", 0x58: "Designator Maximum", 0x78: "String Index",
        0x88: "String Minimum", 0x98: "String Maximum", 0xA8: "Delimiter",
    }
    lines = []
    i = 0; indent = 0
    while i < len(data):
        b = data[i]
        size = b & 3; size = 4 if size == 3 else size
        tag = b & 0xFC
        val = int.from_bytes(data[i+1:i+1+size], "little") if size else 0
        raw = " ".join(f"{x:02x}" for x in data[i:i+1+size])
        name = names.get(tag, f"tag 0x{tag:02x}")
        if tag == 0xC0: indent -= 1
        extra = ""
        if tag in (0x80, 0x90, 0xB0):
            flags = []
            flags.append("Const" if val & 1 else "Data")
            flags.append("Var" if val & 2 else "Array")
            flags.append("Rel" if val & 4 else "Abs")
            if val & 8: flags.append("Wrap")
            if val & 16: flags.append("NonLin")
            if val & 32: flags.append("NoPref")
            if val & 64: flags.append("Null")
            if val & 128: flags.append("Volatile")
            extra = " (" + ",".join(flags) + ")"
        if tag == 0xA0:
            extra = " (" + {0: "Physical", 1: "Application", 2: "Logical"}.get(val, str(val)) + ")"
        lines.append(f"{raw:<14} {'  '*indent}{name} (0x{val:x}){extra}")
        if tag == 0xA0: indent += 1
        i += 1 + size
    return lines

devs = [d for d in hid.enumerate() if d["vendor_id"] == VID]
result = []
for d in devs:
    entry = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in d.items()}
    entry["descriptor"] = None
    entry["descriptor_error"] = None
    try:
        h = hid.device()
        h.open_path(d["path"])
        try:
            desc = bytes(h.get_report_descriptor())
            entry["descriptor"] = desc.hex()
            entry["descriptor_decoded"] = decode_descriptor(desc)
        except Exception as e:
            entry["descriptor_error"] = repr(e)
        try:
            entry["serial"] = h.get_serial_number_string()
        except Exception as e:
            entry["serial_error"] = repr(e)
        h.close()
    except Exception as e:
        entry["open_error"] = repr(e)
    result.append(entry)

with open(os.path.join(out_dir, "hid_enumeration.json"), "w") as f:
    json.dump(result, f, indent=2)

with open(os.path.join(out_dir, "hid_enumeration.txt"), "w") as f:
    for e in result:
        f.write("=" * 78 + "\n")
        f.write(f"path            : {e['path']}\n")
        f.write(f"VID:PID         : {e['vendor_id']:04x}:{e['product_id']:04x}\n")
        f.write(f"manufacturer    : {e.get('manufacturer_string')}\n")
        f.write(f"product         : {e.get('product_string')}\n")
        f.write(f"release/bcd     : 0x{e.get('release_number',0):04x}\n")
        f.write(f"interface       : {e.get('interface_number')}\n")
        f.write(f"usage_page/usage: 0x{e.get('usage_page',0):04x} / 0x{e.get('usage',0):04x}\n")
        f.write(f"bus_type        : {e.get('bus_type')}\n")
        if e.get("open_error"): f.write(f"open_error      : {e['open_error']}\n")
        if e.get("descriptor_error"): f.write(f"descriptor_error: {e['descriptor_error']}\n")
        if e.get("descriptor"):
            f.write(f"descriptor ({len(e['descriptor'])//2} bytes): {e['descriptor']}\n")
            for line in e["descriptor_decoded"]:
                f.write("    " + line + "\n")
        f.write("\n")
print(open(os.path.join(out_dir, "hid_enumeration.txt")).read())
