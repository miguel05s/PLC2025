import argparse
from pathlib import Path

from .lexer import build_lexer
from .parser import build_parser
from .codegen_vm import CodeGen


def compile_source(source: str):
    lexer = build_lexer()
    parser = build_parser()
    ast = parser.parse(source, lexer=lexer)
    codegen = CodeGen()
    instructions = codegen.generate(ast)
    return '\n'.join(instructions)


def main():
    ap = argparse.ArgumentParser(description='Pascal to VM compiler')
    ap.add_argument('input', help='Input Pascal file')
    ap.add_argument('-o', '--output', help='Output VM file (default: stdout)')
    args = ap.parse_args()

    source = Path(args.input).read_text(encoding='utf-8')
    output = compile_source(source)

    if args.output:
        Path(args.output).write_text(output + '\n', encoding='utf-8')
    else:
        print(output)


if __name__ == '__main__':
    main()
