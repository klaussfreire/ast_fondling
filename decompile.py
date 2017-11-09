import ast
import StringIO

class ExpressionDecompilingVisitor(ast.NodeVisitor):

    def visit_Expr(self, n):
        return "(%s)" % (self.visit(n.value),)

    def visit_Tuple(self, n):
        return "(%s)" % (", ".join([self.visit(e) for e in n.elts]))

    def visit_List(self, n):
        return "[%s]" % (", ".join([self.visit(e) for e in n.elts]))

    def visit_ListComp(self, n):
        return "[%s %s]" % (
            self.visit(n.elt),
            " ".join(map(self.visit_comprehension, n.generators))
        )

    def visit_DictComp(self, n):
        return "{%s:%s %s}" % (
            self.visit(n.key), self.visit(n.value),
            " ".join(map(self.visit_comprehension, n.generators))
        )

    def visit_SetComp(self, n):
        return "{%s %s}" % (
            self.visit(n.elt),
            " ".join(map(self.visit_comprehension, n.generators))
        )

    def visit_comprehension(self, n):
        return "for %s in %s%s" % (
            self.visit(n.target),
            self.visit(n.iter),
            ("".join([
                " if %s" % self.visit(_if)
                for _if in n.ifs
            ]) if n.ifs else ""),
        )

    def visit_Set(self, n):
        return "{%s}" % (", ".join([self.visit(e) for e in n.elts]))

    def visit_Num(self, n):
        return repr(n.n)

    def visit_Str(self, n):
        return repr(n.s)

    def visit_Name(self, n):
        return n.id

    def visit_Subscript(self, n):
        return "%s[%s]" % (self.visit(n.value), self.visit(n.slice))

    def visit_Attribute(self, n):
        return "%s.%s" % (self.visit(n.value), n.attr)

    def visit_Index(self, n):
        return self.visit(n.value)

    def visit_ExtSlice(self, n):
        return ":".join(map(self.visit, n.dims))

    def visit_Slice(self, n):
        return "%s:%s%s" % (
            (self.visit(n.lower) if n.lower else ""),
            (self.visit(n.upper) if n.upper else ""),
            (":%s" % (self.visit(n.step),) if n.step else ""),
        )

    def visit_Ellipsis(self, n):
        return "..."

    def visit_Repr(self, n):
        return "repr(%s)" % (self.visit(n.value),)

    def visit_Call(self, n):
        return "%s(%s)" % (self.visit(n.func),
            ", ".join(filter(None, [
                ", ".join(map(self.visit, n.args)),
                ", ".join(["%s=%s" % (k.arg, self.visit(k.value)) for k in n.keywords]),
                ("*%s" % (self.visit(n.starargs),) if n.starargs else None),
                ("**%s" % (self.visit(n.kwargs),) if n.kwargs else None),
            ]))
        )

    def visit_Compare(self, n):
        parts = [self.visit(n.left)]
        cmpops = {
            ast.Eq : '==',
            ast.NotEq : '!=',
            ast.Lt : '<',
            ast.LtE : '<=',
            ast.Gt : '>',
            ast.GtE : '>=',
            ast.Is : 'is',
            ast.IsNot : 'is not',
            ast.In : 'in',
            ast.NotIn : 'not in',
        }
        for op, v in zip(n.ops, n.comparators):
            parts.append(cmpops[type(op)])
            parts.append(self.visit(v))
        return "(%s)" % " ".join(parts)

    def visit_BinOp(self, n):
        binops = {
            ast.Add : '+',
            ast.Sub : '-',
            ast.Mult : '*',
            ast.Div : '/',
            ast.Mod : '%',
            ast.Pow : '**',
            ast.LShift : '<<',
            ast.RShift : '>>',
            ast.BitOr : '|',
            ast.BitXor : '^',
            ast.BitAnd : '&',
            ast.FloorDiv : '//',
        }
        return "(%s)" % " ".join([
            self.visit(n.left),
            binops[type(n.op)],
            self.visit(n.right)
        ])

    def visit_BoolOp(self, n):
        boolops = {
            ast.And : ' and ',
            ast.Or : ' or ',
        }
        return "(%s)" % boolops[type(n.op)].join(map(self.visit, n.values))

    def visit_UnaryOp(self, n):
        unops = {
            ast.Invert : '~',
            ast.Not : 'not',
            ast.UAdd : '+',
            ast.USub : '-',
        }
        return "(%s(%s))" % (unops[type(n.op)], self.visit(n.operand))

    def visit_Lambda(self, n):
        return "(lambda %s:%s)" % (
            self.visit_args(n.args),
            self.visit(n.body)
        )

    def visit_args(self, n):
        ndargs = n.args[:-len(n.defaults)] if n.defaults else n.args
        return ", ".join(filter(None,[
            (", ".join(map(self.visit, ndargs))),
            (", ".join([
                "%s=%s" % (self.visit(a), self.visit(d))
                for a,d in zip(n.args[-len(n.defaults):], n.defaults)
            ])),
            ("*%s" % n.vararg if n.vararg else ""),
            ("**%s" % n.kwarg if n.kwarg else ""),
        ]))

    def visit_IfExp(self, n):
        return "(%s if %s else %s)" % tuple(map(self.visit, [n.body, n.test, n.orelse]))

    def visit_Dict(self, n):
        return "{%s}" % ", ".join([
            "%s : %s" % (self.visit(k), self.visit(v))
            for k,v in zip(n.keys, n.values)
        ])


class StatementDecompilingVisitor(ast.NodeVisitor):

    def __init__(self):
        self.indent = 0
        self.buf = StringIO.StringIO()

    def decompile_expr(self, n):
        return ExpressionDecompilingVisitor().visit(n)

    def emit_line(self, fmt, *p, **kw):
        assert not kw or not p
        fmted = fmt % (p or kw)
        self.buf.write(" "*self.indent + fmted + "\n")

    def visit_Expr(self, n):
        self.emit_line("%s", self.decompile_expr(n.value))

    def visit_Return(self, n):
        self.emit_line("return %s", self.decompile_expr(n.value))

    def visit_Delete(self, n):
        self.emit_line("delete %s", ", ".join(map(self.decompile_expr, n.targets)))

    def visit_Assign(self, n):
        self.emit_line("%s = %s",
            ", ".join(map(self.decompile_expr, n.targets)),
            self.decompile_expr(n.value),
        )

    def visit_AugAssign(self, n):
        binops = {
            ast.Add : '+=',
            ast.Sub : '-=',
            ast.Mult : '*=',
            ast.Div : '/=',
            ast.Mod : '%=',
            ast.Pow : '**=',
            ast.LShift : '<<=',
            ast.RShift : '>>=',
            ast.BitOr : '|=',
            ast.BitXor : '^=',
            ast.BitAnd : '&=',
            ast.FloorDiv : '//=',
        }
        self.emit_line("%s %s %s",
            self.decompile_expr(n.target),
            binops[type(n.op)],
            self.decompile_expr(n.value),
        )

    def visit_Print(self, n):
        parts = []
        if n.dest:
            parts.append(">>" + self.decompile_expr(n.dest))
        parts.extend(map(self.decompile_expr, n.values))
        if not n.nl:
            parts.append("")
        self.emit_line("print %s", ", ".join(parts))

    def visit_For(self, n):
        self.emit_line("for %(target)s in %(iter)s:",
            target = self.decompile_expr(n.target),
            iter = self.decompile_expr(n.iter),
        )
        self.indent_visit(n.body)
        if n.orelse:
            self.emit_line("else:")
            self.indent_visit(n.orelse)

    def visit_While(self, n):
        self.emit_line("while %(test)s:",
            test = self.decompile_expr(n.test),
        )
        self.indent_visit(n.body)
        if n.orelse:
            self.emit_line("else:")
            self.indent_visit(n.orelse)

    def visit_If(self, n, ifelif = 'if'):
        self.emit_line("%(ifelif)s %(test)s:",
            ifelif = ifelif,
            test = self.decompile_expr(n.test)
        )
        self.indent_visit(n.body)
        if n.orelse:
            if len(n.orelse) == 1 and type(n.orelse[0]) == ast.If:
                self.visit_If(n.orelse[0], 'elif')
            else:
                self.emit_line("else:")
                self.indent_visit(n.orelse)

    def visit_With(self, n):
        self.emit_line("with %(expr)s%(asvar)s:",
            expr = self.decompile_expr(n.context_expr),
            asvar = (" as %s" % self.decompile_expr(n.optional_vars) if n.optional_vars else ""),
        )
        self.indent_visit(n.body)

    def visit_Raise(self, n):
        self.emit_line("raise %s", ", ".join(
            map(self.decompile_expr, filter(None, [n.type, n.inst, n.tback]))))

    def visit_TryExcept(self, n):
        self.emit_line("try:")
        self.indent_visit(n.body)
        for h in n.handlers:
            if h.name:
                self.emit_line("except %s as %s:",
                    self.decompile_expr(h.type), self.decompile_expr(h.name))
            else:
                self.emit_line("except %s:", self.decompile_expr(h.type))
            self.indent_visit(h.body)
        if n.orelse:
            self.emit_line("else:")
            self.indent_visit(n.orelse)

    def visit_TryFinally(self, n):
        self.emit_line("try:")
        self.indent_visit(n.body)
        self.emit_line("finally:")
        self.indent_visit(n.finalbody)

    def visit_Assert(self, n):
        self.emit_line("assert %s%s",
            self.decompile_expr(n.test),
            (","+self.decompile_expr(n.msg) if n.msg else "")
        )

    def visit_Import(self, n):
        self.emit_line("import %s", ", ".join(map(self.visit_alias, n.names)))

    def visit_ImportFrom(self, n):
        self.emit_line("from %s import %s",
            "." * (n.level or 0) + (n.module or ''),
            ", ".join(map(self.visit_alias, n.names))
        )

    def visit_Pass(self, n):
        self.emit_line("pass")

    def visit_Continue(self, n):
        self.emit_line("continue")

    def visit_Break(self, n):
        self.emit_line("break")

    def visit_Global(self, n):
        self.emit_line("global %s", ", ".join(n.names))

    def visit_alias(self, n):
        if n.asname:
            return "%s as %s" % (n.name, n.asname)
        else:
            return n.name

    def visit_FunctionDef(self, n):
        for d in n.decorator_list:
            self.emit_line("@%s", self.decompile_expr(d))
        self.emit_line("def %(name)s(%(args)s):",
            name = n.name,
            args = ExpressionDecompilingVisitor().visit_args(n.args),
        )
        self.indent_visit(n.body)

    def visit_ClassDef(self, n):
        for d in n.decorator_list:
            self.emit_line("@%s", self.decompile_expr(d))
        self.emit_line("class %(name)s%(bases)s:",
            name = n.name,
            bases = "(%s)" % (", ".join(map(self.decompile_expr, n.bases))) if n.bases else '',
        )
        self.indent_visit(n.body)

    def indent_visit(self, nl):
        self.indent += 4
        for s in nl:
            self.visit(s)
        self.indent -= 4

def decompile(n):
    v = StatementDecompilingVisitor()
    v.visit(n)
    return v.buf.getvalue()

def decompile_expr(e):
    return ExpressionDecompilingVisitor().visit(e)

