"""Tiny `strings` replacement: prints ASCII and UTF-16LE strings >= min length."""
import re, sys
minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 5
b = open(sys.argv[1], 'rb').read()
for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, b):
    print(m.group().decode())
for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}' % minlen, b):
    print(m.group().decode('utf-16le'))
