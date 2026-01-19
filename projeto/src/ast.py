class Node:
    pass


class Program(Node):
    def __init__(self, name, block):
        self.name = name
        self.block = block


class Subprograms(Node):
    def __init__(self, items):
        self.items = items


class Block(Node):
    def __init__(self, declarations, subprograms, statements):
        self.declarations = declarations  # list of VarDecl
        self.subprograms = subprograms    # list of ProcedureDecl/FunctionDecl
        self.statements = statements      # list of Statement


class VarDecl(Node):
    def __init__(self, name, vartype, size=None):
        self.name = name
        self.vartype = vartype  # Type
        self.size = size        # for arrays (low, high)


class Param(Node):
    def __init__(self, name, vartype, byref=False):
        self.name = name
        self.vartype = vartype
        self.byref = byref


class ProcedureDecl(Node):
    def __init__(self, name, params, block):
        self.name = name
        self.params = params  # list[Param]
        self.block = block


class FunctionDecl(Node):
    def __init__(self, name, params, return_type, block):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.block = block


class Type(Node):
    def __init__(self, name, base=None, range_bounds=None):
        self.name = name
        self.base = base
        self.range_bounds = range_bounds


class Compound(Node):
    def __init__(self, statements):
        self.statements = statements


class Assign(Node):
    def __init__(self, target, expr):
        self.target = target
        self.expr = expr


class Var(Node):
    def __init__(self, name):
        self.name = name


class ArrayAccess(Node):
    def __init__(self, array, index):
        self.array = array
        self.index = index


class If(Node):
    def __init__(self, cond, then_body, else_body=None):
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body


class While(Node):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body


class For(Node):
    def __init__(self, var, start, end, body, downto=False):
        self.var = var
        self.start = start
        self.end = end
        self.body = body
        self.downto = downto


class Repeat(Node):
    def __init__(self, body, cond):
        self.body = body
        self.cond = cond


class ProcCall(Node):
    def __init__(self, name, args):
        self.name = name
        self.args = args


class FuncCall(Node):
    def __init__(self, name, args):
        self.name = name
        self.args = args


class NoOp(Node):
    pass


class BinOp(Node):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right


class UnOp(Node):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr


class Literal(Node):
    def __init__(self, value, typ):
        self.value = value
        self.typ = typ
