"""Parser PLY para o subconjunto Pascal.

Regras grammar->AST: cada função p_* materializa uma produção e devolve nós em ast.*.
Inclui subprogramas, arrays 1D, controlo de fluxo e builtins (readln/writeln, length).
"""

import sys
import ply.yacc as yacc
from .lexer import tokens, build_lexer
from . import ast

precedence = (
    # Atribuição é à direita: a := b := c
    ('right', 'ASSIGN'),
    # Curto-circuito lógico
    ('left', 'OR'),
    ('left', 'AND'),
    # Comparações não associativas evitam encadeamento (< <=)
    ('nonassoc', 'LT', 'LE', 'GT', 'GE', 'EQ', 'NE'),
    # Soma/subtração
    ('left', 'PLUS', 'MINUS'),
    # Multiplicação, divisão inteira e módulo
    ('left', 'TIMES', 'RDIV', 'DIV', 'MOD'),
    # Unários
    ('right', 'NOT'),
    ('right', 'UMINUS'),
)


def p_program(p):
    '''program : PROGRAM ID SEMICOLON block DOT'''
    p[0] = ast.Program(p[2], p[4])


def p_block(p):
    '''block : opt_var_decls opt_subprograms opt_var_decls compound_statement'''
    decls1, subs, decls2, stmts = p[1], p[2], p[3], p[4]
    decls = decls1 + decls2
    p[0] = ast.Block(decls, subs, stmts.statements)


def p_opt_var_decls(p):
    '''opt_var_decls : VAR var_decl_list
                     | empty'''
    if len(p) == 3:
        p[0] = p[2]
    else:
        p[0] = []


def p_var_decl_list(p):
    '''var_decl_list : var_decl_list var_decl
                     | var_decl'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]


def p_var_decl(p):
    '''var_decl : id_list COLON type SEMICOLON'''
    ids = p[1]
    vartype = p[3]
    p[0] = [ast.VarDecl(i, vartype) for i in ids]


def p_id_list(p):
    '''id_list : ID
               | id_list COMMA ID'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_type_basic(p):
    '''type : INTEGER
        | REAL
        | BOOLEAN
        | STRING'''
    p[0] = ast.Type(p[1].lower())


def p_type_array(p):
    '''type : ARRAY LBRACK ICONST DOTDOT ICONST RBRACK OF type'''
    p[0] = ast.Type('array', base=p[8], range_bounds=(p[3], p[5]))


def p_compound_statement(p):
    '''compound_statement : BEGIN statement_list END'''
    p[0] = ast.Compound(p[2])


def p_statement_list(p):
    '''statement_list : statement_list SEMICOLON statement
                      | statement'''
    if len(p) == 2:
        p[0] = [] if isinstance(p[1], ast.NoOp) else [p[1]]
    else:
        tail = [] if isinstance(p[3], ast.NoOp) else [p[3]]
        p[0] = p[1] + tail


def p_statement(p):
    '''statement : assignment_statement
                 | if_statement
                 | while_statement
                 | for_statement
                 | repeat_statement
                 | procedure_statement
                 | compound_statement
                 | empty'''
    p[0] = p[1]


def p_opt_subprograms(p):
    '''opt_subprograms : opt_subprograms subprogram_decl
                       | subprogram_decl
                       | empty'''
    if len(p) == 2:
        if isinstance(p[1], ast.NoOp):
            p[0] = []
        else:
            p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]


def p_subprogram_decl_proc(p):
    '''subprogram_decl : PROCEDURE ID LPAREN opt_params RPAREN SEMICOLON block SEMICOLON'''
    p[0] = ast.ProcedureDecl(p[2], p[4], p[7])


def p_subprogram_decl_func(p):
    '''subprogram_decl : FUNCTION ID LPAREN opt_params RPAREN COLON type SEMICOLON block SEMICOLON'''
    p[0] = ast.FunctionDecl(p[2], p[4], p[7], p[9])


def p_opt_params(p):
    '''opt_params : param_list
                  | empty'''
    p[0] = [] if isinstance(p[1], ast.NoOp) else p[1]


def p_param_list(p):
    '''param_list : param_list SEMICOLON param_section
                  | param_section'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[3]


def p_param_section(p):
    '''param_section : id_list COLON type'''
    ids = p[1]
    typ = p[3]
    p[0] = [ast.Param(i, typ, byref=False) for i in ids]


def p_assignment(p):
    '''assignment_statement : variable ASSIGN expression'''
    p[0] = ast.Assign(p[1], p[3])


def p_variable_id(p):
    '''variable : ID'''
    p[0] = ast.Var(p[1])


def p_variable_array(p):
    '''variable : ID LBRACK expression RBRACK'''
    p[0] = ast.ArrayAccess(ast.Var(p[1]), p[3])


def p_if_statement(p):
    '''if_statement : IF expression THEN statement ELSE statement
                    | IF expression THEN statement'''
    if len(p) == 7:
        p[0] = ast.If(p[2], p[4], p[6])
    else:
        p[0] = ast.If(p[2], p[4])


def p_while_statement(p):
    '''while_statement : WHILE expression DO statement'''
    p[0] = ast.While(p[2], p[4])


def p_repeat_statement(p):
    '''repeat_statement : REPEAT statement_list UNTIL expression'''
    p[0] = ast.Repeat(p[2], p[4])


def p_for_statement(p):
    '''for_statement : FOR ID ASSIGN expression TO expression DO statement
                     | FOR ID ASSIGN expression DOWNTO expression DO statement'''
    downto = (p[5].lower() == 'downto') if isinstance(p[5], str) else False
    if downto:
        p[0] = ast.For(ast.Var(p[2]), p[4], p[6], p[8], downto=True)
    else:
        p[0] = ast.For(ast.Var(p[2]), p[4], p[6], p[8], downto=False)


def p_procedure_statement(p):
    '''procedure_statement : READLN LPAREN expr_list RPAREN
                           | WRITELN LPAREN expr_list RPAREN
                           | READLN LPAREN RPAREN
                           | WRITELN LPAREN RPAREN
                           | ID LPAREN opt_expr_list RPAREN'''
    if p.slice[1].type in ('READLN', 'WRITELN'):
        args = p[3] if len(p) == 5 else []
        p[0] = ast.ProcCall(p[1].lower(), args)
    else:
        p[0] = ast.ProcCall(p[1], p[3])


def p_opt_expr_list(p):
    '''opt_expr_list : expr_list
                     | empty'''
    p[0] = [] if isinstance(p[1], ast.NoOp) else p[1]


def p_expr_list(p):
    '''expr_list : expression
                 | expr_list COMMA expression'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression RDIV expression
                  | expression DIV expression
                  | expression MOD expression
                  | expression EQ expression
                  | expression NE expression
                  | expression LT expression
                  | expression LE expression
                  | expression GT expression
                  | expression GE expression
                  | expression AND expression
                  | expression OR expression'''
    p[0] = ast.BinOp(p[1], p[2].lower() if isinstance(p[2], str) else p[2], p[3])


def p_expression_unary(p):
    '''expression : MINUS expression %prec UMINUS
                  | NOT expression'''
    p[0] = ast.UnOp(p[1].lower() if isinstance(p[1], str) else p[1], p[2])


def p_expression_group(p):
    '''expression : LPAREN expression RPAREN'''
    p[0] = p[2]


def p_expression_call(p):
    '''expression : ID LPAREN opt_expr_list RPAREN'''
    p[0] = ast.FuncCall(p[1], p[3])


def p_expression_length(p):
    '''expression : LENGTH LPAREN expression RPAREN'''
    p[0] = ast.FuncCall('length', [p[3]])


def p_expression_literal(p):
    '''expression : ICONST
                  | FCONST
                  | SCONST
                  | TRUE
                  | FALSE'''
    tok = p.slice[1].type
    if tok == 'ICONST':
        p[0] = ast.Literal(p[1], 'integer')
    elif tok == 'FCONST':
        p[0] = ast.Literal(p[1], 'real')
    elif tok == 'SCONST':
        p[0] = ast.Literal(p[1], 'string')
    elif tok == 'TRUE':
        p[0] = ast.Literal(True, 'boolean')
    else:
        p[0] = ast.Literal(False, 'boolean')


def p_expression_variable(p):
    '''expression : variable'''
    p[0] = p[1]


def p_empty(p):
    '''empty :'''
    p[0] = ast.NoOp()


def p_error(p):
    """Relata erro sintático com lexema e linha."""
    if p:
        raise SyntaxError(f"Syntax error at '{p.value}' (line {p.lineno})")
    raise SyntaxError('Unexpected end of input')


def build_parser():
    """Constroi o parser PLY configurado para a gramática Pascal reduzida."""
    lexer = build_lexer()
    return yacc.yacc(
        debug=False,
        write_tables=False,
        tabmodule=None,
        start='program',
        errorlog=yacc.NullLogger(),
        module=sys.modules[__name__],
    )