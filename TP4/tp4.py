import re

token_specification = [
    ('LIMIT',       r'\bLIMIT\b'),
    ('SELECT',      r'\bSELECT\b'),
    ('WHERE',       r'\bWHERE\b'),
    ('A',           r'\ba\b'),
    ('VAR',         r'\?[a-zA-Z_]\w*'),
    ('URI',         r'[a-zA-Z_][\w\-]*:[\w\-]+'),
    ('LITERAL',     r'"[^"]*"(@[a-z]+)?'),
    ('NUMBER',      r'\d+'),
    ('SYMBOL',      r'[{}.\(\)]'),
    ('IDENT',       r'\b[a-zA-Z_]\w*\b'),  # <- nova regra para 's'
    ('SKIP',        r'[ \t\n]+'),
    ('MISMATCH',    r'.'),
]


tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
get_token = re.compile(tok_regex).match

def lexer(code):
    pos = 0
    tokens = []
    while pos < len(code):
        match = get_token(code, pos)
        if not match:
            raise SyntaxError(f'Caractere inesperado: {code[pos]}')
        kind = match.lastgroup
        value = match.group()
        if kind == 'SKIP':
            pass
        elif kind == 'MISMATCH':
            raise SyntaxError(f'Token inválido: {value}')
        else:
            tokens.append((kind, value))
        pos = match.end()
    return tokens

query = '''
select ?nome ?desc where {
?s a dbo:MusicalArtist.
?s foaf:name "Chuck Berry"@en .
?w dbo:artist ?s.
?w foaf:name ?nome.
?w dbo:abstract ?desc
} LIMIT 1000
'''

if __name__ == "__main__":
    try:
        tokens = lexer(query)
        for token in tokens:
            print(token)
    except SyntaxError as e:
        print(f"Erro de análise léxica: {e}")
