import re

def markdown_para_html(markdown):
    linhas = markdown.split('\n')
    html = []
    lista_numerada = False

    for linha in linhas:
        linha = linha.strip()

        
        if linha.startswith('### '):
            html.append(f"<h3>{linha[4:].strip()}</h3>")
        elif linha.startswith('## '):
            html.append(f"<h2>{linha[3:].strip()}</h2>")
        elif linha.startswith('# '):
            html.append(f"<h1>{linha[2:].strip()}</h1>")

        
        elif re.match(r'^\d+\.\s', linha):
            if not lista_numerada:
                html.append("<ol>")
                lista_numerada = True
            item = re.sub(r'^\d+\.\s', '', linha)
            html.append(f"<li>{item}</li>")
        else:
            if lista_numerada:
                html.append("</ol>")
                lista_numerada = False

            
            linha = re.sub(r'!\[([^\]]+)\]\(([^)]+)\)', r'<img src="\2" alt="\1"/>', linha)

            
            linha = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', linha)

            
            linha = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', linha)

            
            linha = re.sub(r'\*([^\*]+)\*', r'<i>\1</i>', linha)

            html.append(linha)

    if lista_numerada:
        html.append("</ol>")

    return '\n'.join(html)

#exemplo
if __name__ == "__main__":
    markdown_texto = """
# Título Principal
## Subtítulo
### Sub-subtítulo

Este é um **texto em negrito** e este é um *texto em itálico*.

1. Primeiro item
2. Segundo item
3. Terceiro item

Como pode ser consultado em [página da UC](http://www.uc.pt)

Como se vê na imagem seguinte: ![imagem dum coelho](http://www.coellho.com)
"""

    html_resultado = markdown_para_html(markdown_texto)
    print(html_resultado)
