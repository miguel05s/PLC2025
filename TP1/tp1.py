import re

# Expressão regular que reconhece cadeias binárias sem "011"
pattern = re.compile(r"^(?!.*011)[01]*$")  

def aceita_sem_011(s):
    return bool(pattern.fullmatch(s))

testes = ["0", "1", "10", "110", "1111", "001", "011", "1011", "11011", "10010"]

for t in testes:
    print(f"{t:>6} -> {aceita_sem_011(t)}")
