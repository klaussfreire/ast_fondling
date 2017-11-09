import ast

import decompile_js

class ExpressionDecompilingVisitor(decompile_js.ExpressionDecompilingVisitor):

    def visit_Name(self, n):
        builtins = {
            'None' : 'null',
            'True' : 'true',
            'False' : 'false',
        }
        if n.id in builtins:
            return builtins[n.id]
        else:
            return n.id

    def visit_Call(self, n):
        if n.keywords or n.starargs or n.kwargs:
            raise NotImplementedError
        builtins = {
            'int' : 'parseInt',
            'float' : 'parseFloat',
            'str' : 'String',
            'repr' : 'JSON.stringify',
        }
        if isinstance(n.func, ast.Name) and n.func.id in builtins and len(n.args) == 1:
            func = builtins[n.func.id]
        else:
            func = self.visit(n.func)
        return "%s(%s)" % (func,
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
            ast.Add : '(%s + %s)',
            ast.Sub : '(%s - %s)',
            ast.Mult : '(%s * %s)',
            ast.Div : '(%s / %s)',
            ast.Mod : '(%s %% %s)',
            ast.Pow : '(%s ** %s)',
            ast.LShift : '(%s << %s)',
            ast.RShift : '(%s >> %s)',
            ast.BitOr : '(%s | %s)',
            ast.BitXor : '(%s ^ %s)',
            ast.BitAnd : '(%s & %s)',
            ast.FloorDiv : '(parseInt(%s / %s))',
        }
        return binops[type(n.op)] % (
            self.visit(n.left),
            self.visit(n.right),
        )


class StatementDecompilingVisitor(decompile_js.StatementDecompilingVisitor):

    def decompile_expr(self, n):
        return ExpressionDecompilingVisitor().visit(n)

def decompile(n):
    v = StatementDecompilingVisitor()
    v.visit(n)
    return v.buf.getvalue()

def decompile_expr(e):
    return ExpressionDecompilingVisitor().visit(e)

