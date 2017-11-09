from __future__ import print_function

import ast
import sys
import decompile

with open(sys.argv[1], "r") as f:
    root = ast.parse(f.read(), sys.argv[1])

for op in sys.argv[2:]:
    if op == 'constprop':
        import constprop
        root = constprop.ConstPropTransformer().visit(root)
    elif op == 'js':
        import decompile_js as decompile
    elif op == 'js2':
        import decompile_js_v2 as decompile
    elif op == 'inline':
        import inlining
        root = inlining.InlineTransformer().visit(root)

print(decompile.decompile(root))

