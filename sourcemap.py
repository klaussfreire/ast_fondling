from __future__ import print_function

import ast
import sys

with open(sys.argv[1], "r") as f:
    root = ast.parse(f.read(), sys.argv[1])

class mapping_visitor(ast.NodeVisitor):
    def __init__(self):
        self.funcs = {}
        self.classes = {}

    def visit_FunctionDef(self, n):
        self.funcs[(n.name, n.lineno)] = n
        self.generic_visit(n)

    def visit_ClassDef(self, n):
        v = mapping_visitor()
        v.generic_visit(n)
        self.classes[(n.name, n.lineno)] = (n, v)

    def print_map(self, indent = "", functitle = "Functions"):
        if self.funcs:
            print("%s%s:" % (indent, functitle))
            for (fname, lineno), n in sorted(self.funcs.items()):
                print("%s %d: - %s(%s)" % (
                    indent, lineno, fname,
                    ", ".join([a.id for a in n.args.args])
                ))
            print()
        if self.classes:
            print("%sClasses:" % indent)
            for (cname, lineno), (n, body_v) in sorted(self.classes.items()):
                print("%s %d: %s(%s)" % (
                    indent, lineno, cname,
                    ", ".join([b.id for b in n.bases])
                ))
                body_v.print_map(indent + "    ", "Methods")
            print()

v = mapping_visitor()
v.visit(root)
v.print_map()
