import ply.lex as lex
#___________________________________________________________________________________________________________#
#### Definição de Palavras Reservadas ####
'''
Mapa de lexemas reservados para o nome de token que o parser vai consumir. Esta tabela é a primeira
barreira contra identificadores: se o lexema existir aqui, sai com o token específico (ex.: "begin" -> BEGIN);
caso contrário, sai como ID. Isto garante que o parser reconhece construções sintáticas-chave e evita que
palavras da linguagem sejam tratadas como nomes de variáveis.
'''
reserved = {
    'program': 'PROGRAM',
    'var': 'VAR',
    'integer': 'INTEGER',
    'real': 'REAL',
    'boolean': 'BOOLEAN',
    'string': 'STRING',
    'array': 'ARRAY',
    'of': 'OF',
    'begin': 'BEGIN',
    'end': 'END',
    'if': 'IF',
    'then': 'THEN',
    'else': 'ELSE',
    'while': 'WHILE',
    'do': 'DO',
    'for': 'FOR',
    'to': 'TO',
    'downto': 'DOWNTO',
    'repeat': 'REPEAT',
    'until': 'UNTIL',
    'procedure': 'PROCEDURE',
    'function': 'FUNCTION',
    'length': 'LENGTH',
    'div': 'DIV',
    'mod': 'MOD',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
    'true': 'TRUE',
    'false': 'FALSE',
    'readln': 'READLN',
    'writeln': 'WRITELN',
}
#___________________________________________________________________________________________________________#
#### Definição de Tokens ####
'''
Inventário completo de tokens que o lexer pode emitir. Inclui:
- átomos léxicos genéricos (ID, ICONST, FCONST, SCONST);
- operadores aritméticos/relacionais e atribuição;
- delimitadores de agrupamento e separadores;
- todos os tokens correspondentes às reservadas (anexados via list(reserved.values())).
'''
tokens = [
    'ID', 'ICONST', 'FCONST', 'SCONST',
    'PLUS', 'MINUS', 'TIMES', 'RDIV',
    'ASSIGN', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE',
    'LPAREN', 'RPAREN', 'LBRACK', 'RBRACK',
    'SEMICOLON', 'COLON', 'COMMA', 'DOT', 'DOTDOT'
] + list(reserved.values())

#___________________________________________________________________________________________________________#
#### Tokens Simples por Regex ####
'''
Cada variável t_X associa um nome de token a uma regex literal. Estes são tokens de 1–2 caracteres que
não precisam de lógica adicional: operadores (+,-,*,/, :=, =, <>, <=, >=, <, >), parênteses, colchetes,
separadores (; , :) e pontuação (. ..). O PLY gera automaticamente a função de tokenização com base no
nome da variável.
'''
t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_RDIV = r'/'
t_ASSIGN = r':='
t_EQ = r'='
t_NE = r'<>'
t_LE = r'<='
t_GE = r'>='
t_LT = r'<'
t_GT = r'>'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACK = r'\['
t_RBRACK = r'\]'
t_SEMICOLON = r';'
t_COLON = r':'
t_COMMA = r','
t_DOTDOT = r'\.\.'
t_DOT = r'\.'

t_ignore = ' \t'  # ignora espaços e tabs


def t_SCONST(t):
    # Literais de string entre aspas simples; preserva escapes e remove as aspas
    r"'([^'\\]|\\.)*'"
    t.value = t.value[1:-1]
    return t


def t_FCONST(t):
    # Constantes reais com parte decimal e expoente opcional
    r"\d+\.\d+([eE][-+]?\d+)?"
    t.value = float(t.value)
    return t


def t_ICONST(t):
    # Constantes inteiras decimais
    r"\d+"
    t.value = int(t.value)
    return t


def t_ID(t):
    # Identificadores; converte para token de palavra reservada se aplicável
    r"[A-Za-z_][A-Za-z0-9_]*"
    t.type = reserved.get(t.value.lower(), 'ID')
    t.value = t.value
    return t


def t_newline(t):
    # Contagem de novas linhas para rastrear números de linha
    r"\n+"
    t.lexer.lineno += len(t.value)


def t_comment_brace(t):
    # Comentários { ... }
    r"\{[^}]*\}"
    t.lexer.lineno += t.value.count('\n')


def t_comment_paren(t):
    # Comentários (* ... *), modo DOTALL
    r"\(\*[\s\S]*?\*\)"
    t.lexer.lineno += t.value.count('\n')


def t_error(t):
    '''Lança SyntaxError ao encontrar caractere ilegal, indicando o símbolo e a linha.'''
    raise SyntaxError(f"Illegal character '{t.value[0]}' at line {t.lexer.lineno}")


def build_lexer():
    '''Constroi e devolve o lexer PLY configurado.'''
    return lex.lex()