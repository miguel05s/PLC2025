# TP3- Conversor de Markdown para HTML

## Autor 
- **Nome:** Miguel Silva  
- **ID:** A109069
- **Foto:**
- <img src="unipic.jpg" alt="Foto" width="120"/>



Este projeto foi desenvolvido para a disciplina de **Processamento de Linguagens e Compiladores** e consiste num pequeno conversor de texto em formato Markdown para HTML, utilizando Python.

---

## Funcionalidades

O conversor reconhece e transforma os seguintes elementos da sintaxe Markdown:

###  Cabeçalhos
- `# Título` → `<h1>Título</h1>`
- `## Subtítulo` → `<h2>Subtítulo</h2>`
- `### Sub-subtítulo` → `<h3>Sub-subtítulo</h3>`

###  Negrito e Itálico
- `**texto**` → `<b>texto</b>`
- `*texto*` → `<i>texto</i>`

### Lista Numerada
Markdown:
```markdown
1. Primeiro item  
2. Segundo item  
3. Terceiro item
```
HTML:
```
<ol>
  <li>Item 1</li>
  <li>Item 2</li>
</ol>
```
Links
```
[texto](url) → <a href="url">texto</a>
```
Imagens
```
![alt](url) → <img src="url" alt="alt"/>
```
###Como usar

Cria um ficheiro tpc3.md com o conteúdo Markdown.

Executa o script Python tp3.py.

O resultado será gravado automaticamente em tpc3.html.




