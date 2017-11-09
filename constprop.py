import ast

class ConstPropTransformer(ast.NodeTransformer):

    def make_const(self, val, n):
        if isinstance(val, (list, tuple, set)):
            if isinstance(val, list):
                ntype = ast.List
            elif isinstance(val, tuple):
                ntype = ast.Tuple
            elif isinstance(val, set):
                ntype = ast.Set
            else:
                raise AssertionError
            return ast.copy_location(ntype(
                elts = map(self.make_const, val),
                ctx = n.ctx,
            ), n)
        elif val is True or val is False or val is None:
            return ast.copy_location(ast.Name(id=str(val)), n)
        elif isinstance(val, (int, long, float)):
            return ast.copy_location(ast.Num(n=val), n)
        elif isinstance(val, basestring):
            return ast.copy_location(ast.Str(s=val), n)

    def get_value(self, n):
        if isinstance(n, ast.Name):
            builtins = {
                'None' : None,
                'True' : True,
                'False' : False,
            }
            return builtins[n.id]
        elif isinstance(n, ast.Num):
            return n.n
        elif isinstance(n, ast.Str):
            return n.s
        elif isinstance(n, (ast.List, ast.Set, ast.Tuple)):
            if isinstance(n, list):
                ltype = list
            elif isinstance(n, tuple):
                ltype = tuple
            elif isinstance(n, set):
                ltype = set
            return ltype(map(self.get_value, n.elts))

    def is_const(self, n):
        if isinstance(n, ast.Name):
            return n.id in ('None', 'True', 'False' )
        elif isinstance(n, (ast.Num, ast.Str)):
            return True
        elif isinstance(n, (ast.List, ast.Set, ast.Tuple)):
            return all(map(self.is_const, n.elts))
        return False

    def visit_UnaryOp(self, n):
        n.value = self.visit(n.value)
        if self.is_const(n.value):
            unops = {
                ast.Invert : lambda x : ~x,
                ast.Not : lambda x : not x,
                ast.UAdd : lambda x : +x,
                ast.USub : lambda x : -x,
            }
            return self.make_const(unops[type(n.op)](self.get_value(n.value)), n)
        return n

    def visit_BinOp(self, n):
        n.left = self.visit(n.left)
        n.right = self.visit(n.right)
        if self.is_const(n.left) and self.is_const(n.right):
            binops = {
                ast.Add : lambda l,r : l+r,
                ast.Sub : lambda l,r : l-r,
                ast.Mult : lambda l,r : l*r,
                ast.Div : lambda l,r : l/r,
                ast.Mod : lambda l,r : l%r,
                ast.Pow : lambda l,r : l**r,
                ast.LShift : lambda l,r : l<<r,
                ast.RShift : lambda l,r : l>>r,
                ast.BitOr : lambda l,r : l|r,
                ast.BitXor : lambda l,r : l^r,
                ast.BitAnd : lambda l,r : l&r,
                ast.FloorDiv : lambda l,r : l//r,
            }
            return self.make_const(binops[type(n.op)](
                self.get_value(n.left),
                self.get_value(n.right),
            ), n)
        return n

    def visit_Compare(self, n):
        n.left = self.visit(n.left)
        n.comparators = [ self.visit(v) for v in n.comparators ]
        cmpops = {
            ast.Eq : lambda l,r:l==r,
            ast.NotEq : lambda l,r:l!=r,
            ast.Lt : lambda l,r:l<r,
            ast.LtE : lambda l,r:l<=r,
            ast.Gt : lambda l,r:l>r,
            ast.GtE : lambda l,r:l>=r,
            ast.Is : lambda l,r:l is r,
            ast.IsNot : lambda l,r:l is not r,
            ast.In : lambda l,r:l in r,
            ast.NotIn : lambda l,r:l not in r,
        }
        if self.is_const(n.left) and all(map(self.is_const, n.comparators)):
            prev = self.get_value(n.left)
            rv = True
            for op, v in zip(n.ops, n.comparators):
                cur = self.get_value(v)
                rv = cmpops[type(op)](prev, cur)
                prev = cur
                if not rv:
                    break
            return self.make_const(rv, n)
        else:
            return n

    def visit_BoolOp(self, n):
        n.values = [ self.visit(v) for v in n.values ]
        if all(map(self.is_const, n.values)):
            def bool_and(values):
                rv = values[0]
                if rv:
                    for v in values[1:]:
                        rv = rv and v
                        if not rv:
                            break
                return rv
            def bool_or(values):
                rv = values[0]
                if not rv:
                    for v in values[1:]:
                        rv = rv or v
                        if rv:
                            break
                return rv
            boolops = {
                ast.And : bool_and,
                ast.Or : bool_or,
            }
            return self.make_const(
                boolops[type(n.op)](map(self.get_value, n.values)),
                n
            )
        else:
            return n

    def visit_IfExp(self, n):
        n.test = self.visit(n.test)
        n.body = self.visit(n.body)
        n.orelse = self.visit(n.orelse)
        if self.is_const(n.test):
            if self.get_value(n.test):
                return n.body
            else:
                return n.orelse
        else:
            return n

    def visit_Call(self, n):
        n = self.generic_visit(n)
        if (        isinstance(n.func, ast.Name)
                    and (not n.args or all(map(self.is_const, n.args)))
                    and (not n.keywords or all(map(self.is_const, [kw.arg for kw in n.keywords])))
                    and (not n.starargs or self.is_const(n.starargs))
                    and (not n.kwargs or self.is_const(n.kwargs))
                ):
            builtins = {
                'str' : str,
                'int' : int,
                'float' : float,
                'long' : long,
                'bool' : bool,
            }
            f = builtins.get(n.func.id)
            if f is not None:
                args = map(self.get_value, n.args)
                if n.kwargs:
                    kwargs = self.get_value(n.kwargs)
                else:
                    kwargs = {}
                if n.starargs:
                    starargs = list(self.get_value(n.starargs))
                else:
                    starargs = []
                if n.keywords:
                    kwargs.update({ kw.id : self.get_value(kw.arg) for kw in n.keywords })
                return self.make_const(f(*(args + starargs), **kwargs), n)
        return n
