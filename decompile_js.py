import ast
import StringIO
import json

class ExpressionDecompilingVisitor(ast.NodeVisitor):

    def visit_Expr(self, n):
        return "(%s)" % (self.visit(n.value),)

    def visit_Tuple(self, n):
        return "[%s]" % (", ".join([self.visit(e) for e in n.elts]))

    def visit_List(self, n):
        return "[%s]" % (", ".join([self.visit(e) for e in n.elts]))

    def visit_Set(self, n):
        return "{%s}" % (", ".join(["%s:true" % self.visit(e) for e in n.elts]))

    def visit_ListComp(self, n):
        return "(function(){ var rv=[]; %(fors)s rv.push(%(exp)s); %(closing_fors)s ; return rv; })()" % dict(
            closing_fors = "}}" * len(n.generators),
            exp = self.visit(n.elt),
            fors = " ".join(map(self.visit_comprehension, n.generators))
        )

    def visit_DictComp(self, n):
        return "(function(){ var rv={}; %(fors)s rv[%(key)s] = %(val)s; %(closing_fors)s ; return rv;  })()" % dict(
            closing_fors = "}}" * len(n.generators),
            key = self.visit(n.key),
            val = self.visit(n.value),
            fors = " ".join(map(self.visit_comprehension, n.generators))
        )

    def visit_SetComp(self, n):
        return "(function(){ var rv={}; %(fors)s rv[%(exp)s] = true; %(closing_fors)s ; return rv;  })()" % dict(
            closing_fors = "}}" * len(n.generators),
            exp = self.visit(n.elt),
            fors = " ".join(map(self.visit_comprehension, n.generators))
        )

    def visit_comprehension(self, n):
        return "{ var __iter = %(iter)s; for (var %(tgt)s in __iter) { %(tgt)s = __iter[%(tgt)s]; %(ifs)s" % dict(
            tgt = self.visit(n.target),
            iter = self.visit(n.iter),
            ifs = (" if (!(%s)) continue; " % " && ".join([
                "(%s)" % self.visit(_if)
                for _if in n.ifs
            ]) if n.ifs else ""),
        )

    def visit_Num(self, n):
        return json.dumps(n.n)

    def visit_Str(self, n):
        return json.dumps(n.s)

    def visit_Name(self, n):
        return n.id

    def visit_Subscript(self, n):
        return "%s[%s]" % (self.visit(n.value), self.visit(n.slice))

    def visit_Attribute(self, n):
        return "%s.%s" % (self.visit(n.value), n.attr)

    def visit_Index(self, n):
        return self.visit(n.value)

    def visit_ExtSlice(self, n):
        raise NotImplementedError

    def visit_Slice(self, n):
        raise NotImplementedError

    def visit_Ellipsis(self, n):
        raise NotImplementedError

    def visit_Repr(self, n):
        return "JSON.stringify(%s)" % (self.visit(n.value),)

    def visit_Call(self, n):
        if n.keywords or n.starargs or n.kwargs:
            raise NotImplementedError
        return "%s(%s)" % (self.visit(n.func),
            ", ".join(filter(None, [
                ", ".join(map(self.visit, n.args)),
            ]))
        )

    def visit_Compare(self, n):
        parts = []
        cmpops = {
            ast.Eq : '(%s == %s)',
            ast.NotEq : '(%s != %s)',
            ast.Lt : '(%s < %s)',
            ast.LtE : '(%s <= %s)',
            ast.Gt : '(%s > %s)',
            ast.GtE : '(%s >= %s)',
            ast.Is : '(%s === %s)',
            ast.IsNot : '(%s !== %s)',
            ast.In : '(%s in %s)',
            ast.NotIn : '!(%s in %s))',
        }
        prev = self.visit(n.left)
        for op, v in zip(n.ops, n.comparators):
            cur = self.visit(v)
            parts.append(cmpops[type(op)] % (prev, cur))
            prev = cur
        return "(%s)" % " && ".join(parts)

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
            ast.FloorDiv : '/',
        }
        return "(%s)" % " ".join([
            self.visit(n.left),
            binops[type(n.op)],
            self.visit(n.right)
        ])

    def visit_BoolOp(self, n):
        boolops = {
            ast.And : ' && ',
            ast.Or : ' || ',
        }
        return "(%s)" % boolops[type(n.op)].join(map(self.visit, n.values))

    def visit_UnaryOp(self, n):
        unops = {
            ast.Invert : '~',
            ast.Not : '!',
            ast.UAdd : '+',
            ast.USub : '-',
        }
        return "(%s(%s))" % (unops[type(n.op)], self.visit(n.operand))

    def visit_Lambda(self, n):
        return "(function(%s){ return %s; })" % (
            self.visit_args(n.args),
            self.visit(n.body)
        )

    def visit_args(self, n):
        if n.defaults or n.vararg or n.kwarg:
            raise NotImplementedError
        ndargs = n.args[:-len(n.defaults)] if n.defaults else n.args
        return ", ".join(filter(None,[
            (", ".join(map(self.visit, ndargs))),
        ]))

    def visit_IfExp(self, n):
        return "((%s)?(%s):(%s))" % tuple(map(self.visit, [n.test, n.body, n.orelse]))

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
        extra_indent = kw.pop('extra_indent', 0)
        assert not kw or not p
        fmted = fmt % (p or kw)
        self.buf.write(" "*(self.indent + extra_indent) + fmted + "\n")

    def visit_Expr(self, n):
        self.emit_line("%s;", self.decompile_expr(n.value))

    def visit_Return(self, n):
        self.emit_line("return %s;", self.decompile_expr(n.value))

    def visit_Delete(self, n):
        self.emit_line("%s = undefined;", ", ".join(map(self.decompile_expr, n.targets)))

    def visit_Assign(self, n):
        self.emit_line("%s = %s;",
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
            ast.FloorDiv : '/=',
        }
        self.emit_line("%s %s %s;",
            self.decompile_expr(n.target),
            binops[type(n.op)],
            self.decompile_expr(n.value),
        )

    def visit_Print(self, n):
        parts = []
        if n.dest:
            raise NotImplementedError
        parts.extend(map(self.decompile_expr, n.values))
        if not n.nl:
            raise NotImplementedError
        self.emit_line("console.log(%s);", ", ".join(parts))

    def visit_For(self, n):
        self.emit_line("{ var __iter = %(iter)s ; for (var %(target)s in __iter) { %(target)s = __iter[%(target)s];",
            target = self.decompile_expr(n.target),
            iter = self.decompile_expr(n.iter),
        )
        self.indent_visit(n.body)
        if n.orelse:
            raise NotImplementedError
        self.emit_line("}}")

    def visit_While(self, n):
        self.emit_line("while (%(test)s) {",
            test = self.decompile_expr(n.test),
        )
        self.indent_visit(n.body)
        if n.orelse:
            raise NotImplementedError
        self.emit_line("}")

    def visit_If(self, n, ifelif = 'if'):
        self.emit_line("%(ifelif)s (%(test)s) {",
            ifelif = ifelif,
            test = self.decompile_expr(n.test)
        )
        self.indent_visit(n.body)
        if n.orelse:
            if len(n.orelse) == 1 and type(n.orelse[0]) == ast.If:
                self.visit_If(n.orelse[0], '} else if')
            else:
                self.emit_line("} else {")
                self.indent_visit(n.orelse)
        self.emit_line("}")

    def visit_With(self, n):
        raise NotImplementedError

    def visit_Raise(self, n):
        if n.tback:
            raise NotImplementedError
        if n.inst:
            self.emit_line("throw %s;", self.decompile_expr(n.inst))
        elif n.type:
            self.emit_line("throw %s();", self.decompile_expr(n.type))
        else:
            raise NotImplementedError

    def visit_TryExcept(self, n):
        self.emit_line("try {")
        self.indent_visit(n.body)
        for h in n.handlers:
            if h.name:
                self.emit_line("} catch (%s) {",
                    self.decompile_expr(h.name))
            else:
                self.emit_line("} catch (_unused) {")
            self.indent_visit(h.body)
        if n.orelse:
            raise NotImplementedError()
        self.emit_line("}")

    def visit_TryFinally(self, n):
        self.emit_line("try {")
        self.indent_visit(n.body)
        self.emit_line("} catch(_err) {")
        self.indent_visit(n.finalbody)
        self.emit_line("throw _err;", extra_indent=4)
        self.emit_line("}")
        self.visit(n.finalbody)

    def visit_Assert(self, n):
        self.emit_line("if (!(%s)) { throw %s; }",
            self.decompile_expr(n.test),
            (","+self.decompile_expr(n.msg) if n.msg else '"AssertionError"')
        )

    def visit_Import(self, n):
        raise NotImplementedError()

    def visit_ImportFrom(self, n):
        raise NotImplementedError()

    def visit_Pass(self, n):
        pass

    def visit_Continue(self, n):
        self.emit_line("continue;")

    def visit_Break(self, n):
        self.emit_line("break;")

    def visit_Global(self, n):
        pass

    def visit_alias(self, n):
        if n.asname:
            raise NotImplementedError
        else:
            return n.name

    def visit_FunctionDef(self, n):
        for d in n.decorator_list:
            raise NotImplementedError
        self.emit_line("function %(name)s(%(args)s) {",
            name = n.name,
            args = ExpressionDecompilingVisitor().visit_args(n.args),
        )
        self.indent_visit(n.body)
        self.emit_line("}")

    def visit_ClassDef(self, n):
        raise NotImplementedError

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

