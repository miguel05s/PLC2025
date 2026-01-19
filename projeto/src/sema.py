from . import ast


class SemanticError(Exception):
    pass


class Symbol:
    def __init__(self, name, typ, kind='var', size=1, base=None, bounds=None):
        self.name = name
        self.typ = typ
        self.kind = kind
        self.size = size
        self.base = base
        self.bounds = bounds


class SymbolTable:
    def __init__(self):
        self.stack = [dict()]

    def push(self):
        self.stack.append(dict())

    def pop(self):
        self.stack.pop()

    def declare(self, name, sym):
        if name.lower() in self.stack[-1]:
            raise SemanticError(f"Symbol '{name}' redeclared")
        self.stack[-1][name.lower()] = sym

    def lookup(self, name):
        lname = name.lower()
        for scope in reversed(self.stack):
            if lname in scope:
                return scope[lname]
        raise SemanticError(f"Undeclared identifier '{name}'")


class Analyzer:
    def __init__(self):
        self.table = SymbolTable()

    def analyze(self, node):
        if isinstance(node, ast.Program):
            return self.visit_program(node)
        raise SemanticError('Invalid AST root')

    def visit_program(self, node):
        self.visit_block(node.block)
        return self.table

    def visit_block(self, node):
        for decl in node.declarations:
            for d in decl:
                self.declare_var(d)
        for sub in getattr(node, 'subprograms', []) or []:
            self.visit_subprogram(sub)
        for stmt in node.statements:
            self.visit_statement(stmt)

    def visit_subprogram(self, sub):
        # Enter new scope for params/locals
        self.table.push()
        if hasattr(sub, 'params'):
            for p in sub.params:
                self.declare_param(p)
        if isinstance(sub, ast.FunctionDecl):
            # function identifier acts as variable for return
            self.table.declare(sub.name, Symbol(sub.name, sub.return_type.name if isinstance(sub.return_type, ast.Type) else sub.return_type, kind='func'))
        self.visit_block(sub.block)
        self.table.pop()

    def declare_var(self, decl):
        typ = decl.vartype
        bounds = typ.range_bounds
        size = 1
        base_type = typ.name
        if typ.name == 'array':
            size = (bounds[1] - bounds[0] + 1)
            base_type = typ.base.name
        sym = Symbol(decl.name, base_type, kind='var', size=size, base=decl.vartype.base, bounds=bounds)
        self.table.declare(decl.name, sym)

    def declare_param(self, param):
        typ = param.vartype
        base_type = typ.name if isinstance(typ, ast.Type) else typ
        sym = Symbol(param.name, base_type, kind='param')
        self.table.declare(param.name, sym)

    def visit_statement(self, node):
        if isinstance(node, ast.Assign):
            ltype = self.visit_lvalue(node.target)
            rtype = self.visit_expr(node.expr)
            if ltype != rtype and not (ltype == 'real' and rtype == 'integer'):
                raise SemanticError(f'Type mismatch in assignment to {node.target.name}')
        elif isinstance(node, ast.If):
            cond = self.visit_expr(node.cond)
            if cond != 'boolean':
                raise SemanticError('Condition in if must be boolean')
            for s in node.then_body.statements if isinstance(node.then_body, ast.Compound) else [node.then_body]:
                self.visit_statement(s)
            if node.else_body:
                for s in node.else_body.statements if isinstance(node.else_body, ast.Compound) else [node.else_body]:
                    self.visit_statement(s)
        elif isinstance(node, ast.While):
            if self.visit_expr(node.cond) != 'boolean':
                raise SemanticError('Condition in while must be boolean')
            for s in node.body.statements if isinstance(node.body, ast.Compound) else [node.body]:
                self.visit_statement(s)
        elif isinstance(node, ast.For):
            self.table.lookup(node.var.name)
            self.visit_expr(node.start)
            self.visit_expr(node.end)
            for s in node.body.statements if isinstance(node.body, ast.Compound) else [node.body]:
                self.visit_statement(s)
        elif isinstance(node, ast.Repeat):
            for s in node.body:
                self.visit_statement(s)
            if self.visit_expr(node.cond) != 'boolean':
                raise SemanticError('Condition in repeat must be boolean')
        elif isinstance(node, ast.ProcCall):
            for arg in node.args:
                self.visit_expr(arg)
        elif isinstance(node, ast.Compound):
            for s in node.statements:
                self.visit_statement(s)
        elif isinstance(node, ast.NoOp):
            return
        else:
            raise SemanticError(f'Unknown statement {node}')

    def visit_lvalue(self, node):
        if isinstance(node, ast.Var):
            sym = self.table.lookup(node.name)
            return sym.typ
        if isinstance(node, ast.ArrayAccess):
            sym = self.table.lookup(node.array.name)
            self.visit_expr(node.index)
            return sym.base.name if sym.base else sym.typ
        raise SemanticError('Invalid lvalue')

    def visit_expr(self, node):
        if isinstance(node, ast.Literal):
            return node.typ
        if isinstance(node, ast.Var):
            return self.table.lookup(node.name).typ
        if isinstance(node, ast.ArrayAccess):
            self.visit_expr(node.index)
            sym = self.table.lookup(node.array.name)
            return sym.base.name if sym.base else sym.typ
        if isinstance(node, ast.FuncCall):
            if node.name.lower() == 'length':
                return 'integer'
            # Unknown function: assume integer result for now
            try:
                sym = self.table.lookup(node.name)
                return sym.typ
            except SemanticError:
                return 'integer'
        if isinstance(node, ast.BinOp):
            lt = self.visit_expr(node.left)
            rt = self.visit_expr(node.right)
            op = node.op
            if op in ('+', '-', '*', '/', 'div', 'mod'):
                if lt == 'real' or rt == 'real' or op == '/':
                    return 'real'
                return 'integer'
            if op in ('<', '<=', '>', '>=', '=', '<>'):
                return 'boolean'
            if op in ('and', 'or'):
                return 'boolean'
        if isinstance(node, ast.UnOp):
            t = self.visit_expr(node.expr)
            if node.op == 'not':
                return 'boolean'
            return t
        raise SemanticError('Invalid expression')