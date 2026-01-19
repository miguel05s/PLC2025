# Pascal para VM

Compilador em Python (PLY) que traduz um subconjunto de Pascal para a VM fornecida no enunciado.

## Uso

Instalação de dependências:

```
pip install ply
```

Compilar:

```
python -m src.main tests/entrada.pas -o examples/saida.vm
```
Se omitir `-o`, escreve para stdout. Os `.vm` não estão no repo; gere-os ao vivo para a defesa.

## Subconjunto suportado
- Tipos: integer, real, boolean, string; arrays 1D com limites inteiros constantes.
- Controlo: if/else, while, repeat/until, for to/downto.
- I/O: readln (variáveis e elementos de array), writeln (expressões), writes implícito via múltiplos args.
- Expressões: +, -, *, /, div, mod, and, or, not, comparações. Concatenação de strings com `+`. `length(s)` e indexação de string `s[i]` (i é 1-based em Pascal, convertido para 0-based na VM).
- Subprogramas: procedure e function sem parâmetros `var`; parâmetros por valor; locais; funções retornam via slot local 1 e também deixam o valor no topo antes de RETURN.

## Convenção de chamada (VM)
- Argumentos: offsets negativos relativizados a `fp`. Último argumento em `PUSHL -1`, penúltimo em `PUSHL -2`, etc. Caller empilha argumentos na ordem escrita e faz `PUSHA FNname` + `CALL`.
- Locais: offsets positivos a partir de 1. Reservamos espaço com `PUSHN k` no prólogo do subprograma.
- Retorno de função: armazenado em `STOREL 1` e também deixado no topo antes de `RETURN` para o caller consumir.
- Globals: guardados em `gp`; `PUSHG/STOREG` com offsets atribuídos pelo compilador.

## Limitações conhecidas
- Sem parâmetros `var`, sem records, sem arrays multidimensionais, sem `case`.
- Não há verificações de bounds em arrays/strings (sem `CHECK`).
- Sem otimizações.

## Exemplos
Fontes Pascal em `tests/`:
- `tests/hello.pas`
- `tests/fatorial.pas`
- `tests/primo.pas`
- `tests/soma_array.pas`
- `tests/binario.pas`

Para gerar cada `.vm` :

- `python -m src.main tests/hello.pas -o examples/hello.vm`
- `python -m src.main tests/fatorial.pas -o examples/fatorial.vm`
- `python -m src.main tests/primo.pas -o examples/primo.vm`
- `python -m src.main tests/soma_array.pas -o examples/soma_array.vm`
- `python -m src.main tests/binario.pas -o examples/binario.vm`


