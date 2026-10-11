"""Translation coverage check: every tr("...") literal, preset label, help text and key group must have a
Slovenian entry, and every key id must have a Slovenian label.  Exit code 1 when something is missing."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from igorskeys import i18n, editor, config  # noqa: E402

lits = set()
for fn in ('igorskeys/editor.py', 'igorskeys/app.py', 'main.py'):
    tree = ast.parse(open(fn, encoding='utf-8').read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'tr' and node.args:
            a = node.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                lits.add(a.value)
lits |= set(editor.TYPE_TEXT.values()) | {l for l, _ in editor.KEY_PRESETS} | {l for l, _, _ in editor.OPEN_PRESETS}
lits |= {editor.HELP_KEYS, editor.HELP_OPEN, editor.HELP_SEQ} | set(i18n.LANGUAGES.values())
keys = config.Keys(os.path.join('igorskeys', 'keys.json'))
lits |= set(keys.groups())
same_in_both = {"English", "Slovenščina", "Google", "YouTube", "Gmail"}
missing = sorted(l for l in lits if l not in i18n.SL and l not in same_in_both)
unused = sorted(k for k in i18n.SL if k not in lits)
labels_missing = [k.id for k in keys.keys if k.id not in i18n.KEY_LABELS_SL]
print("literals checked:", len(lits))
print("missing Slovenian:", missing)
print("unused Slovenian entries:", unused)
print("key labels missing:", labels_missing)
sys.exit(1 if missing or labels_missing else 0)
