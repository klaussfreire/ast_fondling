import ast
import copy

class ReplaceContextTransformer(ast.NodeTransformer):

    def __init__(self, context):
        self.context = context

    def visit_Name(self, n):
        return self.context.get(n.id, n)

class InlineTransformer(ast.NodeTransformer):

    def __init__(self):
        self.funcdefs = {}

    def is_inlineable_expr(self, funcdef, call):
        if call.starargs or call.kwargs:
            return False
        if len(funcdef.body) != 1 or not isinstance(funcdef.body[0], ast.Return):
            return False
        if funcdef.args.args and not all([ isinstance(a, ast.Name) for a in funcdef.args.args ]):
            return False
        if len(funcdef.args.args) != len(call.args):
            return False
        return True

    def get_inline_expr(self, funcdef, call):
        context = {}
        if funcdef.args.vararg:
            context[funcdef.args.vararg] = ast.List(elts=[])
        if funcdef.args.kwarg:
            context[funcdef.arg.kwarg] = ast.Dict(elts=[])
        for func_arg, call_arg in zip(funcdef.args.args, call.args):
            context[func_arg.id] = call_arg

        return ReplaceContextTransformer(context).visit(copy.deepcopy(funcdef.body[0].value))

    def visit_FunctionDef(self, n):
        fdef = self.funcdefs.get(n.name, True)
        if fdef is True:
            # First time
            self.funcdefs[n.name] = n
        else:
            # More than one definition not inlineable
            self.funcdefs[n.name] = None
        return n

    def visit_Call(self, n):
        if isinstance(n.func, ast.Name) and self.funcdefs.get(n.func.id):
            fdef = self.funcdefs.get(n.func.id)
            if self.is_inlineable_expr(fdef, n):
                return self.get_inline_expr(fdef, n)
        elif isinstance(n.func, ast.Lambda):
            fdef = ast.FunctionDef(
                name='<lambda>',
                args=n.func.args,
                body=[ast.Return(value=n.func.body)]
            )
            if self.is_inlineable_expr(fdef, n):
                return self.get_inline_expr(fdef, n)
        return n
