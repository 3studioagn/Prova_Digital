# Referencias visuais do Figma — Wave 3 v4.0 / Componente 10

## Como adicionar os PNGs ao repositorio

A imagem oficial do Figma para o redesign de `/escanear` foi enviada
pelo Mario como anexo na mensagem inicial do Gate 1. Como anexos de
prompt nao ficam no filesystem, os PNGs nao foram commitados
automaticamente.

**Para adicionar permanentemente:**

1. Exportar os 2 frames do Figma em PNG (resolucao 1x ou 2x):
   - Frame 1: pagina `/escanear` em **modo Camera ativo**.
   - Frame 2: pagina `/escanear` em **modo Manual ativo**.

2. Salvar com os nomes:
   - `docs/wave3-v4-c10/figma-reference-camera.png`
   - `docs/wave3-v4-c10/figma-reference-manual.png`

3. Commitar com mensagem `docs(wave3-v4/c10): adiciona referencias do
   Figma`.

## Conteudo das imagens (para revisores que nao tem o Figma)

A `analysis.md` Secao 5.3 e o `smoke-validation.md` descrevem
textualmente os 2 estados visuais com hierarquia clara dos elementos.

Resumo:

### Imagem 1 — Modo Camera
- Sidebar preta com nav (Dashboard, Provas, Nova prova, Escanear, etc.).
- h1 "Escanear prova" + subtitulo.
- Toggle pill: **Camera** (ativo, preto) | Manual (inativo, branco).
- Card cinza claro com 2 colunas:
  - Esquerda (1.2fr): subcard branco com QR mockado + brackets +
    legenda "Centralize o QR Code no quadro".
  - Direita (1fr): h2 "Pronto para escanear" + descricao + botao
    "Abrir camera".
- Footer: "Ultima leitura ha 2 min" + "Ver historico →".

### Imagem 2 — Modo Manual
- Sidebar e header identicos.
- Toggle pill: Camera (inativo, branco) | **Manual** (ativo, preto).
- Card central unico:
  - h2 "Inserir codigo manualmente".
  - Descricao "Digite o codigo... `PRV-AAAA-MM-NNNNNN`".
  - Input com placeholder do formato.
  - Botao escuro "Buscar prova →" (desabilitado quando vazio).
- Mesmo footer.

## Divergencia visual reconhecida vs implementacao

O Figma original mostrava:
- Placeholder do input manual: `3S- XXXX-XXXX` (8 chars, prefixo "3S-").
- Texto "codigo de 8 digitos" na descricao.

A implementacao usa o **formato real ja em producao** (Wave 2 v4.0,
ADR-116 + C06):
- Placeholder: `PRV-AAAA-MM-NNNNNN` (18 chars, prefixo "PRV-").
- Texto: "Digite o codigo da etiqueta no formato
  `<code>PRV-AAAA-MM-NNNNNN</code>`".

**Justificativa:** Q4 do pre-Gate-2 — Mario aprovou "Vamos seguir o
que ja estamos fazendo". O formato `PRV-AAAA-MM-NNNNNN` ja esta
embutido no QR Code (segundo campo) e o `validar_formato_codigo_publico`
do backend rejeita qualquer outro formato. O placeholder visual
precisa ser fiel a esse contrato. Decisao registrada em `DECISIONS.md`
ADR-134 (este Componente 10 v4.0).

Se o Figma for atualizado em algum momento futuro para refletir
`PRV-...`, esta divergencia desaparece automaticamente.
