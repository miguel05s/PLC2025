from . import ast
from .sema import Analyzer


class CodeGenError(Exception):
    pass


class CodeGen:
    def __init__(self):
        self.instructions = []
        self.label_id = 0
        self.global_offsets = {}
        self.global_arrays = {}
        self.global_types = {}
        self.retval_offset = None
        self.temp_offsets = []
        self.temp_depth = 0
        self.symtab = None
        self.current_env = None  # maps name -> (kind, typ, offset, extra)

    def mangle_label(self, name: str) -> str:
        safe = ''.join(ch for ch in name if ch.isalnum())
        return safe or 'FN'

    def new_label(self, base='L'):
        name = f"{base}{self.label_id}"
        self.label_id += 1
        return name

    def emit(self, line):
        self.instructions.append(line)

    def generate(self, program):
        analyzer = Analyzer()
        self.symtab = analyzer.analyze(program)
        self.layout_globals(program)
        main_label = 'MAIN'
        self.emit('START')
        self.emit(f'JUMP {main_label}')
        # emit subprograms first
        for sub in program.block.subprograms:
            self.emit_subprogram(sub)
        # main block
        self.emit(f'{main_label}:')
        self.current_env = None
        self.init_arrays()
        self.emit_block(program.block, scope_env=None)
        self.emit('STOP')
        return self.instructions

    def layout_globals(self, program):
        offset = 0
        for decl_group in program.block.declarations:
            for decl in decl_group:
                name = decl.name.lower()
                self.global_offsets[name] = offset
                self.global_types[name] = decl.vartype
                if decl.vartype.name == 'array':
                    self.global_arrays[name] = decl.vartype
                offset += 1
        # reserve a global slot for function return values to avoid fp/sp ambiguity
        self.retval_offset = offset
        self.global_offsets['__retval'] = offset
        self.global_types['__retval'] = ast.Type('integer')
        offset += 1
        # reserve several global temp slots to spill operands across CALLs
        temp_count = 4
        for i in range(temp_count):
            name = f'__tmp{i}'
            self.global_offsets[name] = offset
            self.global_types[name] = ast.Type('integer')
            self.temp_offsets.append(offset)
            offset += 1

    def init_arrays(self):
        for name, typ in self.global_arrays.items():
            low, high = typ.range_bounds
            size = high - low + 1
            self.emit(f'PUSHI {size}')
            self.emit('ALLOCN')
            off = self.global_offsets[name]
            self.emit(f'STOREG {off}')

    def emit_block(self, block, scope_env):
        prev_env = self.current_env
        if scope_env is not None:
            self.current_env = scope_env
        for stmt in block.statements:
            self.emit_statement(stmt)
        if scope_env is not None:
            self.current_env = prev_env

    def build_env_for_sub(self, sub):
        env = {}
        # parameters: last param at fp[-1] (VM CALL sets fp to sp after popping return addr)
        param_count = len(sub.params)
        for idx, p in enumerate(sub.params):
            off = idx - param_count
            env[p.name.lower()] = ('param', p.vartype, off, None)
        # locals and return slot
        locals_list = []
        for decl_group in sub.block.declarations:
            for decl in decl_group:
                locals_list.append((decl.name.lower(), decl.vartype))
        # function return slot
        local_offset_start = 1
        if isinstance(sub, ast.FunctionDecl):
            env[sub.name.lower()] = ('ret', sub.return_type, local_offset_start, None)
            local_offset_start += 1
        off = local_offset_start
        for name, typ in locals_list:
            env[name] = ('local', typ, off, None)
            off += 1
        local_count = off - 1
        return env, local_count

    def emit_subprogram(self, sub):
        label = self.mangle_label(f'FN{sub.name}')
        env, local_count = self.build_env_for_sub(sub)
        self.emit(f'{label}:')
        if local_count > 0:
            self.emit(f'PUSHN {local_count}')
        self.emit_block(sub.block, scope_env=env)
        if isinstance(sub, ast.FunctionDecl):
            ret_entry = env[sub.name.lower()]
            _, ret_type, ret_off, _ = ret_entry
            # place return value at its dedicated slot (ret_off)
            self.emit_load_offset(ret_off, ret_type)
            self.emit(f'STOREL {ret_off}')
            # also store in reserved global so caller can read reliably
            self.emit_load_offset(ret_off, ret_type)
            self.emit(f'STOREG {self.retval_offset}')
        self.emit('RETURN')

    def emit_statement(self, stmt):
        if isinstance(stmt, ast.Assign):
            val_type = self.emit_expression(stmt.expr)
            self.emit_store(stmt.target, val_type)
        elif isinstance(stmt, ast.If):
            l_else = self.new_label('ELSE')
            l_end = self.new_label('ENDIF')
            self.emit_expression(stmt.cond)
            self.emit(f'JZ {l_else}')
            self.emit_statement(stmt.then_body)
            self.emit(f'JUMP {l_end}')
            self.emit(f'{l_else}:')
            if stmt.else_body:
                self.emit_statement(stmt.else_body)
            self.emit(f'{l_end}:')
        elif isinstance(stmt, ast.While):
            l_start = self.new_label('WH')
            l_end = self.new_label('WHE')
            self.emit(f'{l_start}:')
            self.emit_expression(stmt.cond)
            self.emit(f'JZ {l_end}')
            self.emit_statement(stmt.body)
            self.emit(f'JUMP {l_start}')
            self.emit(f'{l_end}:')
        elif isinstance(stmt, ast.For):
            self.emit_assignment(stmt.var, stmt.start)
            l_start = self.new_label('FOR')
            l_end = self.new_label('FORE')
            self.emit(f'{l_start}:')
            self.emit_load(stmt.var)
            end_type = self.emit_expression(stmt.end)
            self.ensure_type('integer', end_type)
            if stmt.downto:
                self.emit('SUPEQ')
            else:
                self.emit('INFEQ')
            self.emit(f'JZ {l_end}')
            self.emit_statement(stmt.body)
            self.emit_load(stmt.var)
            self.emit(f'PUSHI { -1 if stmt.downto else 1}')
            self.emit('ADD')
            self.emit_store(stmt.var, 'integer')
            self.emit(f'JUMP {l_start}')
            self.emit(f'{l_end}:')
        elif isinstance(stmt, ast.Repeat):
            l_start = self.new_label('REP')
            self.emit(f'{l_start}:')
            for s in stmt.body:
                self.emit_statement(s)
            self.emit_expression(stmt.cond)
            self.emit(f'JZ {l_start}')
        elif isinstance(stmt, ast.ProcCall):
            if stmt.name == 'writeln':
                for arg in stmt.args:
                    t = self.emit_expression(arg)
                    self.emit_write(t)
                self.emit('WRITELN')
            elif stmt.name == 'readln':
                for arg in stmt.args:
                    self.emit_read_into(arg)
            else:
                # user-defined procedure
                self.emit_call(stmt.name, stmt.args, expect_result=False)
        elif isinstance(stmt, ast.Compound):
            for s in stmt.statements:
                self.emit_statement(s)
        elif isinstance(stmt, ast.NoOp):
            return
        else:
            raise CodeGenError(f'Unsupported statement {stmt}')

    def emit_read_into(self, target):
        self.emit('READ')
        if isinstance(target, (ast.Var, ast.ArrayAccess)):
            target_type = self.get_lvalue_type(target)
            if target_type == 'integer':
                self.emit('ATOI')
            elif target_type == 'real':
                self.emit('ATOF')
            elif target_type == 'boolean':
                self.emit('ATOI')
            self.emit_store(target, target_type)
        else:
            raise CodeGenError('readln expects variables')

    def emit_write(self, expr_type):
        if expr_type == 'integer' or expr_type == 'boolean':
            self.emit('WRITEI')
        elif expr_type == 'real':
            self.emit('WRITEF')
        elif expr_type == 'string':
            self.emit('WRITES')
        else:
            raise CodeGenError('Unsupported type in writeln')

    def emit_assignment(self, var, expr):
        t = self.emit_expression(expr)
        self.emit_store(var, t)

    def emit_store(self, target, val_type):
        if isinstance(target, ast.Var):
            target_type, kind, off = self.resolve_name(target.name)
            if target_type == 'real' and val_type == 'integer':
                self.emit('ITOF')
                val_type = 'real'
            self.ensure_type(target_type, val_type)
            self.emit_store_offset(off, kind)
        elif isinstance(target, ast.ArrayAccess):
            base_type, kind, base_off = self.resolve_name(target.array.name)
            # string indexing handled differently
            if base_type == 'string':
                # cannot store into string char
                raise CodeGenError('Cannot assign to string character')
            arr_typ = self.get_array_type(target.array.name)
            low = arr_typ.range_bounds[0]
            target_type = arr_typ.base.name
            if target_type == 'real' and val_type == 'integer':
                self.emit('ITOF')
                val_type = 'real'
            self.ensure_type(target_type, val_type)
            # spill value to temp to rebuild stack as (addr, idx, val)
            temp_slot = self.temp_offsets[0]
            self.emit(f'STOREG {temp_slot}')
            self.emit_push_address(base_off, kind)
            idx_type = self.emit_expression(target.index)
            self.ensure_type('integer', idx_type)
            if low != 0:
                self.emit(f'PUSHI {low}')
                self.emit('SUB')
            self.emit(f'PUSHG {temp_slot}')
            self.emit_store_index(target_type)
        else:
            raise CodeGenError('Invalid assignment target')

    def emit_store_index(self, val_type):
        # Stack: base, index, value should be in that order for STOREN
        if val_type == 'real':
            self.emit('STOREN')
        else:
            self.emit('STOREN')

    def emit_load(self, var):
        if isinstance(var, ast.Var):
            typ, kind, off = self.resolve_name(var.name)
            self.emit_load_offset(off, kind)
            return self.normalize_type(typ)
        if isinstance(var, ast.ArrayAccess):
            base_type, kind, base_off = self.resolve_name(var.array.name)
            if base_type == 'string':
                self.emit_push_address(base_off, kind)
                idx_type = self.emit_expression(var.index)
                self.ensure_type('integer', idx_type)
                # adjust from 1-based to 0-based for VM CHARAT
                self.emit('PUSHI 1')
                self.emit('SUB')
                self.emit('CHARAT')
                return 'integer'
            arr_typ = self.get_array_type(var.array.name)
            low = arr_typ.range_bounds[0]
            self.emit_push_address(base_off, kind)
            idx_type = self.emit_expression(var.index)
            self.ensure_type('integer', idx_type)
            if low != 0:
                self.emit(f'PUSHI {low}')
                self.emit('SUB')
            self.emit('LOADN')
            return arr_typ.base.name
        raise CodeGenError('Invalid load')

    def emit_expression(self, expr):
        if isinstance(expr, ast.Literal):
            if expr.typ == 'integer' or expr.typ == 'boolean':
                self.emit(f'PUSHI {int(expr.value)}')
            elif expr.typ == 'real':
                self.emit(f'PUSHF {float(expr.value)}')
            elif expr.typ == 'string':
                self.emit(f'PUSHS "{self.escape_string(expr.value)}"')
            return expr.typ
        if isinstance(expr, ast.Var):
            return self.emit_load(expr)
        if isinstance(expr, ast.ArrayAccess):
            return self.emit_load(expr)
        if isinstance(expr, ast.BinOp):
            # handle char literal vs integer compare
            if expr.op in ('=', '<>'):
                if isinstance(expr.left, ast.Literal) and expr.left.typ == 'string' and len(str(expr.left.value)) == 1 and not isinstance(expr.right, ast.Literal):
                    expr = ast.BinOp(ast.Literal(ord(expr.left.value), 'integer'), expr.op, expr.right)
                elif isinstance(expr.right, ast.Literal) and expr.right.typ == 'string' and len(str(expr.right.value)) == 1 and not isinstance(expr.left, ast.Literal):
                    expr = ast.BinOp(expr.left, expr.op, ast.Literal(ord(expr.right.value), 'integer'))
            temp_slot = self.temp_offsets[self.temp_depth]
            self.temp_depth += 1
            try:
                lt = self.emit_expression(expr.left)
                # spill left to dedicated temp to survive nested CALLs when evaluating right
                self.emit(f'STOREG {temp_slot}')
                rt = self.emit_expression(expr.right)
                self.emit(f'PUSHG {temp_slot}')
                self.emit('SWAP')
            finally:
                self.temp_depth -= 1
            op = expr.op
            if op in ('+', '-', '*', 'div', 'mod', '/',):
                res_type = self.numeric_result(lt, rt, op)
                self.coerce_stack(lt, rt, res_type)
                self.emit_numeric_op(op, res_type)
                return res_type
            if op in ('<', '<=', '>', '>=', '=', '<>'):
                res_type = 'boolean'
                cmp_type = 'real' if lt == 'real' or rt == 'real' else 'integer'
                self.coerce_stack(lt, rt, cmp_type)
                self.emit_compare(op, cmp_type)
                return res_type
            if op in ('and', 'or'):
                self.emit(op.upper())
                return 'boolean'
            if op == '+':
                if lt == 'string' and rt == 'string':
                    self.emit('CONCAT')
                    return 'string'
            raise CodeGenError(f'Unsupported binary op {op}')
        if isinstance(expr, ast.UnOp):
            t = self.emit_expression(expr.expr)
            if expr.op == 'not':
                self.emit('NOT')
                return 'boolean'
            if expr.op == '-':
                if t == 'real':
                    self.emit('PUSHF 0.0')
                else:
                    self.emit('PUSHI 0')
                self.emit('SWAP')
                op = 'FSUB' if t == 'real' else 'SUB'
                self.emit(op)
                return t
            raise CodeGenError(f'Unsupported unary op {expr.op}')
        if isinstance(expr, ast.FuncCall):
            if expr.name.lower() == 'length':
                t = self.emit_expression(expr.args[0])
                if t != 'string':
                    # convert non-string to string before STRLEN
                    self.emit('STRI')
                self.emit('STRLEN')
                return 'integer'
            # user-defined function
            self.emit_call(expr.name, expr.args, expect_result=True)
            # assume declared type
            return self.lookup_type(expr.name)
        raise CodeGenError(f'Unsupported expression {expr}')

    def emit_call(self, name, args, expect_result):
        # push args in order
        for a in args:
            self.emit_expression(a)
        self.emit(f'PUSHA {self.mangle_label(f"FN{name}")}')
        self.emit('CALL')
        if expect_result:
            # retrieve return value from reserved global slot
            self.emit(f'PUSHG {self.retval_offset}')

    def resolve_name(self, name):
        lname = name.lower()
        if self.current_env and lname in self.current_env:
            kind, typ, off, _ = self.current_env[lname]
            return self.normalize_type(typ), kind, off
        if lname in self.global_offsets:
            typ = self.global_types[lname]
            return self.normalize_type(typ), 'global', self.global_offsets[lname]
        raise CodeGenError(f'Unknown identifier {name}')

    def get_array_type(self, name):
        lname = name.lower()
        if self.current_env and lname in self.current_env:
            typ = self.current_env[lname][1]
            return typ
        return self.global_arrays[lname]

    def emit_push_address(self, off, kind):
        if kind == 'global':
            self.emit(f'PUSHG {off}')
        else:
            self.emit(f'PUSHL {off}')

    def emit_load_offset(self, off, kind_or_typ):
        # kind_or_typ may be a kind string ('param','local','ret','global')
        # or a type in some call sites; default to local when unclear.
        if isinstance(kind_or_typ, str) and kind_or_typ in ('param', 'local', 'ret', 'global'):
            kind = kind_or_typ
        else:
            kind = 'local'
        if kind in ('param', 'local', 'ret'):
            self.emit(f'PUSHL {off}')
        elif kind == 'global':
            self.emit(f'PUSHG {off}')

    def emit_store_offset(self, off, kind):
        if kind in ('param', 'local', 'ret'):
            self.emit(f'STOREL {off}')
        elif kind == 'global':
            self.emit(f'STOREG {off}')

    def lookup_type(self, name):
        lname = name.lower()
        if self.current_env and lname in self.current_env:
            return self.normalize_type(self.current_env[lname][1])
        if lname in self.global_types:
            return self.normalize_type(self.global_types[lname])
        return 'integer'

    def normalize_type(self, typ):
        if isinstance(typ, ast.Type):
            return typ.name
        return typ

    def escape_string(self, s: str) -> str:
        # Escape characters for VM string literal using double quotes
        return s.replace('\\', '\\\\').replace('"', '\\"')

    def numeric_result(self, lt, rt, op):
        if op == '/':
            return 'real'
        if lt == 'real' or rt == 'real':
            return 'real'
        return 'integer'

    def coerce_numeric(self, lt, rt, target):
        # Returns flags to convert top then next to target real
        lt_conv = target == 'real' and lt == 'integer'
        rt_conv = target == 'real' and rt == 'integer'
        return lt_conv, rt_conv

    def coerce_stack(self, lt, rt, target):
        if target != 'real':
            return
        if rt == 'integer':
            self.emit('ITOF')
        if lt == 'integer':
            self.emit('SWAP')
            self.emit('ITOF')
            self.emit('SWAP')

    def emit_numeric_op(self, op, typ):
        if op == '+':
            self.emit('FADD' if typ == 'real' else 'ADD')
        elif op == '-':
            self.emit('FSUB' if typ == 'real' else 'SUB')
        elif op == '*':
            self.emit('FMUL' if typ == 'real' else 'MUL')
        elif op == '/':
            self.emit('FDIV')
        elif op == 'div':
            self.emit('DIV')
        elif op == 'mod':
            self.emit('MOD')
        else:
            raise CodeGenError(f'Unknown numeric op {op}')

    def emit_compare(self, op, typ):
        if op == '<':
            self.emit('FINF' if typ == 'real' else 'INF')
        elif op == '<=':
            self.emit('FINFEQ' if typ == 'real' else 'INFEQ')
        elif op == '>':
            self.emit('FSUP' if typ == 'real' else 'SUP')
        elif op == '>=':
            self.emit('FSUPEQ' if typ == 'real' else 'SUPEQ')
        elif op == '=':
            self.emit('EQUAL')
        elif op == '<>':
            self.emit('EQUAL')
            self.emit('NOT')
        else:
            raise CodeGenError(f'Unknown compare op {op}')

    def ensure_type(self, expected, found):
        if expected == 'real' and found == 'integer':
            return
        if expected != found:
            raise CodeGenError(f'Type mismatch: expected {expected}, got {found}')

    def get_lvalue_type(self, lvalue):
        if isinstance(lvalue, ast.Var):
            sym = self.symtab.lookup(lvalue.name)
            return sym.typ
        if isinstance(lvalue, ast.ArrayAccess):
            typ = self.get_array_type(lvalue.array.name)
            return typ.base.name
        raise CodeGenError('Invalid lvalue')