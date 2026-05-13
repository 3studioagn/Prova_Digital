# Contrato para o Componente 12 — Timeline Visual com 4 Rotas e Laminação

**Origem:** Wave 3 v4.0 / Componente 11 (entregue).
**Consumidor:** Wave 3 v4.0 / Componente 12 (próximo).
**Status:** ATIVO — leitura obrigatória do prompt do C12.

Este documento descreve **tudo** que o C12 (Timeline Visual) precisa consumir do que foi entregue pelo C11. Nada aqui deve ser duplicado no C12; o C12 importa e usa.

---

## 1. Mapeamento de estados → metadata visual

### 1.1 Localização

**`frontend/src/lib/types/prova.ts`** — fonte única de verdade dos tipos + labels.

### 1.2 Tipos exportados

```typescript
/**
 * StatusProva — 17 valores totais (10 v3.0 + 7 v4.0).
 *
 * Wave 3 v4.0 / C11: migration 013 adicionou 7 valores; tipo
 * sincronizado com Postgres + Python (validado em
 * `backend/tests/test_status_prova_enum_drift.py`).
 */
export type StatusProva =
  // Legacy v3.0 (10)
  | "CRIADA"
  | "RETIRADA_PELO_VENDEDOR"
  | "APROVADA_PELO_VENDEDOR"
  | "DE_VOLTA_3STUDIO"
  | "COM_MOTORISTA"
  | "ENVIADA_PARA_CLICHERIA"
  | "ENCAMINHADA_A_CLICHERIA"
  | "RECEBIDA_PELA_CLICHERIA"
  | "REPROVADA_PELO_VENDEDOR"
  | "CANCELADA"
  // v4.0 — 3 contextos do Motorista (US-006 v4.0)
  | "COM_MOTORISTA_IDA_LAMINACAO"
  | "COM_MOTORISTA_VOLTA_LAMINACAO"
  | "COM_MOTORISTA_ENTREGA_FINAL"
  // v4.0 — Etapas de laminação
  | "ENCAMINHADA_PARA_LAMINACAO"
  | "LAMINACAO_CONCLUIDA"
  // v4.0 — Pós-laminação (apenas Lam. Matriz)
  | "DE_VOLTA_3STUDIO_POS_LAMINACAO"
  // v4.0 — Vendedor Filial recebe direto (Filial, Lam. Filial)
  | "ENCAMINHADA_PARA_O_VENDEDOR";
```

### 1.3 Labels canônicos (pt-BR)

```typescript
import { STATUS_LABELS, STATUS_LABELS_SHORT } from "@/lib/types/prova";

// Labels completos — para timeline desktop + detalhe da prova
STATUS_LABELS[status];        // "Com motorista (ida laminacao)"
STATUS_LABELS[status];        // "Encaminhada para laminacao"
STATUS_LABELS[status];        // "Laminacao concluida"

// Labels curtos — para timeline mobile + listagem
STATUS_LABELS_SHORT[status];  // "Ida laminacao"
STATUS_LABELS_SHORT[status];  // "P/ laminar"
STATUS_LABELS_SHORT[status];  // "Laminada"
```

`Record<StatusProva, string>` — TypeScript impõe exhaustividade no nível de compilação.

### 1.4 Paleta de cores sugerida (consumida pelo `ReportGeral`)

O componente `frontend/src/app/(dashboard)/relatorios/perspectivas/ReportGeral.tsx` define `STATUS_DONUT_COLOR: Record<StatusProva, string>`. C12 pode reutilizar:

| Categoria | Cores | Estados |
|---|---|---|
| Inicial | `var(--color-accent, #ffcb5c)` | CRIADA |
| Laminação | `#c0ca33`, `#9ccc65`, `#fbc02d` | ENCAMINHADA_PARA_LAMINACAO, LAMINACAO_CONCLUIDA, DE_VOLTA_3STUDIO_POS_LAMINACAO |
| Motorista | `#ffa726`, `#ff9800`, `#ff7043`, `#ff8a3d` (legacy) | 3 contextos v4.0 + COM_MOTORISTA legacy |
| Vendedor (recebimento) | `#ffd97a`, `#ffe082` | RETIRADA_PELO_VENDEDOR, ENCAMINHADA_PARA_O_VENDEDOR |
| Aprovação | `#f5b041` | APROVADA_PELO_VENDEDOR |
| Devolução 3Studio | `#f1c40f` | DE_VOLTA_3STUDIO |
| Clicheria (em trânsito) | `#e67e22`, `#d35400` | ENVIADA_PARA_CLICHERIA, ENCAMINHADA_A_CLICHERIA (legacy) |
| Terminal sucesso | `#34d399` | RECEBIDA_PELA_CLICHERIA |
| Reprovação | `#d4d4d4` | REPROVADA_PELO_VENDEDOR |
| Cancelamento | `#9ca3af` | CANCELADA |

C12 deve documentar suas próprias cores quando criar a paleta da timeline; este mapeamento é só uma sugestão estável.

---

## 2. Helpers de detecção de contexto do Motorista

### 2.1 Localização

**Backend Python:** `backend/app/state_machine/v4/contextos.py`

```python
from app.state_machine.v4.contextos import (
    ContextoMotorista,
    contexto_motorista,
)
```

### 2.2 API

```python
ContextoMotorista = Literal["ida_laminacao", "volta_laminacao", "entrega_final"]

def contexto_motorista(status: StatusProvaEnum) -> ContextoMotorista | None:
    """Deriva o contexto do motorista a partir do status."""
```

Mapeamento:
- `COM_MOTORISTA_IDA_LAMINACAO` → `"ida_laminacao"`
- `COM_MOTORISTA_VOLTA_LAMINACAO` → `"volta_laminacao"`
- `COM_MOTORISTA_ENTREGA_FINAL` → `"entrega_final"`
- `COM_MOTORISTA` (legacy v3.0) → `"entrega_final"` (compat)
- Qualquer outro status → `None`

### 2.3 Onde encontrar o contexto persistido

Cada `Movimentacao` v4.0 grava o contexto em `audit_log.detalhes_json.contexto_motorista`:

```python
# Exemplo de detalhes_json gravado pelo executar_transicao_v4:
{
    "de": "DE_VOLTA_3STUDIO",
    "para": "COM_MOTORISTA_ENTREGA_FINAL",
    "ciclo": 1,
    "rota_antes": "MATRIZ",
    "rota_depois": "MATRIZ",
    "maquina": "v4",
    "contexto_motorista": "entrega_final"
}
```

C12 pode:
- **(A) Derivar em tempo de render** chamando `contexto_motorista(movimentacao.status_novo)` no frontend.
  - Implementação TS recomendada (espelho do Python):
    ```typescript
    type ContextoMotorista = "ida_laminacao" | "volta_laminacao" | "entrega_final";

    export function contextoMotorista(status: StatusProva): ContextoMotorista | null {
      if (status === "COM_MOTORISTA_IDA_LAMINACAO") return "ida_laminacao";
      if (status === "COM_MOTORISTA_VOLTA_LAMINACAO") return "volta_laminacao";
      if (status === "COM_MOTORISTA_ENTREGA_FINAL") return "entrega_final";
      if (status === "COM_MOTORISTA") return "entrega_final";  // legacy
      return null;
    }
    ```
- **(B) Consumir do `audit_log` via novo endpoint** se o C12 precisar do histórico de contextos para movimentações antigas (improvável — derivar é mais simples).

**Recomendação técnica para C12:** Opção A. O derivação client-side é 8 linhas, sem ida ao backend.

### 2.4 Renderização visual sugerida

| Contexto | Sugestão visual | Onde aparece (rotas) |
|---|---|---|
| `ida_laminacao` | Badge "→ Laminação" | Lam. Matriz, Lam. Filial |
| `volta_laminacao` | Badge "Laminação →" | Lam. Matriz apenas |
| `entrega_final` | Badge "→ Clicheria" | Matriz, Lam. Matriz |
| `null` (não-motorista) | sem badge | — |

---

## 3. Sequência canônica de etapas por rota

### 3.1 Localização

**Backend Python:** `backend/app/state_machine/v4/rules.py` — função `estados_da_rota(rota)`.

```python
from app.state_machine.v4.rules import estados_da_rota

estados_da_rota(RotaEnum.MATRIZ)
# frozenset({CRIADA, RETIRADA_PELO_VENDEDOR, APROVADA_PELO_VENDEDOR,
#            DE_VOLTA_3STUDIO, COM_MOTORISTA_ENTREGA_FINAL,
#            RECEBIDA_PELA_CLICHERIA})

estados_da_rota(RotaEnum.LAM_MATRIZ)
# frozenset com 11 valores cobrindo a rota completa
```

**Frontend (a criar pelo C12):** `frontend/src/lib/types/prova.ts` ou módulo dedicado pode exportar:

```typescript
export const ROTA_ETAPAS: Record<RotaCriacao, StatusProva[]> = {
  MATRIZ: [
    "CRIADA",
    "RETIRADA_PELO_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "DE_VOLTA_3STUDIO",
    "COM_MOTORISTA_ENTREGA_FINAL",
    "RECEBIDA_PELA_CLICHERIA",
  ],
  LAM_MATRIZ: [
    "CRIADA",
    "ENCAMINHADA_PARA_LAMINACAO",
    "COM_MOTORISTA_IDA_LAMINACAO",
    "LAMINACAO_CONCLUIDA",
    "COM_MOTORISTA_VOLTA_LAMINACAO",
    "DE_VOLTA_3STUDIO_POS_LAMINACAO",
    "RETIRADA_PELO_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "DE_VOLTA_3STUDIO",
    "COM_MOTORISTA_ENTREGA_FINAL",
    "RECEBIDA_PELA_CLICHERIA",
  ],
  FILIAL: [
    "CRIADA",
    "ENCAMINHADA_PARA_O_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "RECEBIDA_PELA_CLICHERIA",
  ],
  LAM_FILIAL: [
    "CRIADA",
    "ENCAMINHADA_PARA_LAMINACAO",
    "COM_MOTORISTA_IDA_LAMINACAO",
    "LAMINACAO_CONCLUIDA",
    "ENCAMINHADA_PARA_O_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "RECEBIDA_PELA_CLICHERIA",
  ],
};
```

**Atenção:** sequência **incluindo `CRIADA`** + **excluindo** `REPROVADA_PELO_VENDEDOR` e `CANCELADA` (transversais). C12 deve renderizar `REPROVADA` e `CANCELADA` como ramificações visuais, não como nós na linha principal.

### 3.2 Provas legacy v3.0 (rota IS NULL ou PADRAO/DIRETA)

C12 deve renderizar legacy via mapeamento separado:

```typescript
// Para provas legacy (rota=NULL, PADRAO ou DIRETA):
const LEGACY_ROTA_PADRAO: StatusProva[] = [
  "CRIADA",
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "DE_VOLTA_3STUDIO",
  "COM_MOTORISTA",
  "ENVIADA_PARA_CLICHERIA",
  "RECEBIDA_PELA_CLICHERIA",
];

const LEGACY_ROTA_DIRETA: StatusProva[] = [
  "CRIADA",
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "ENCAMINHADA_A_CLICHERIA",
  "RECEBIDA_PELA_CLICHERIA",
];
```

A timeline do C12 pode usar isto até a Wave 7 fazer o backfill final. Provas v4.0 sempre têm `rota IN {MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL}`.

---

## 4. Estado atual e progresso da prova

### 4.1 Como detectar a etapa atual

Dado `prova.status` e `prova.rota`:

1. Pegue a sequência canônica: `ROTA_ETAPAS[prova.rota]` (v4.0) ou legacy se aplicável.
2. Encontre o índice de `prova.status` na sequência: `etapas.indexOf(prova.status)`.
3. Renderize etapas anteriores como **concluídas**, atual como **em andamento**, futuras como **pendentes**.

**Casos especiais:**
- `prova.status === "CANCELADA"`: renderize toda a timeline com badge de cancelamento sobre a etapa anterior + linha vermelha para indicar interrupção. `prova.motivo_cancelamento` contém o motivo.
- `prova.status === "REPROVADA_PELO_VENDEDOR"`: timeline volta a "CRIADA" (novo ciclo); o ciclo anterior fica preservado em `movimentacoes` com `ciclo=N` e `motivo_reprovacao`.
- `prova.rota IS NULL` (legacy v3.0 não-backfilled): fallback para sequência v3.0 baseada no histórico.

### 4.2 Múltiplos ciclos (RF-009 v4.0)

Quando uma prova é reprovada e o ciclo é reiniciado, `prova.ciclo_atual` incrementa (+1). Cada movimentação carrega `ciclo: N`. C12 pode:
- Renderizar uma timeline por ciclo, com separador visual.
- Ou colapsar ciclos anteriores em uma aba ("Ciclo 1", "Ciclo 2 atual").

Filtrar movimentações por ciclo: `movimentacoes.filter(m => m.ciclo === prova.ciclo_atual)`.

### 4.3 Rota imutável (RN-002 v4.0)

`prova.rota` é definido na criação (C06) e nunca muda. C12 pode hardcoding a rota no header da timeline com confiança.

---

## 5. Endpoints e dados a consumir

### 5.1 Lista canônica

| Endpoint | Uso pelo C12 | Notas |
|---|---|---|
| `GET /api/v1/provas/{id}` | Carrega prova completa | `ProvaResponse` — inclui `rota`, `status`, `ciclo_atual`, `motivo_cancelamento`, `codigo_publico` |
| `GET /api/v1/provas/{id}/movimentacoes` | Histórico cronológico | `MovimentacaoListResponse` — JOIN com usuário, inclui `motivo_reprovacao`, `rota_no_momento`, `ciclo` |

### 5.2 Campo a observar em movimentações

```typescript
interface MovimentacaoResponse {
  id: string;
  prova_id: string;
  usuario_id: string;
  usuario_nome: string;
  usuario_setor: Setor;  // "STUDIO" | "VENDEDOR" | "MOTORISTA" | "CLICHERIA"
  status_anterior: StatusProva;
  status_novo: StatusProva;
  motivo_reprovacao: string | null;
  ciclo: number;
  rota_no_momento: Rota | null;
  created_at: string;  // ISO timestamp
}
```

Não exposto na API (server-side only): `assinatura_digital`, `audit_log.detalhes_json`. Se C12 precisar do `contexto_motorista` da auditoria, deve derivar via `contextoMotorista(m.status_novo)`.

---

## 6. Animações e a11y

### 6.1 prefers-reduced-motion (RN-012 v4.0)

C12 **deve** respeitar:

```css
@media (prefers-reduced-motion: reduce) {
  .timeline-step-enter {
    transition: none !important;
    animation: none !important;
  }
}
```

Validar manualmente ativando `prefers-reduced-motion: reduce` no DevTools antes do PR.

### 6.2 Framer Motion já no projeto

Já há um `framer-motion` instalado (Wave 6 + Wave 3 v4.0 C10 usando `layoutId` + `AnimatePresence`). C12 pode reutilizar.

### 6.3 ARIA

- Timeline com `role="list"` e cada etapa `role="listitem"`.
- Etapa atual: `aria-current="step"`.
- Etapas concluídas: `aria-label="<label> — concluído"`.
- Etapa pendente: `aria-label="<label> — pendente"`.

---

## 7. Patterns a NÃO duplicar

### 7.1 Validação de transições

C12 é **só visualização**. Para qualquer botão de transição (se C12 vier a expor algum), consumir:

```typescript
// Já existe — usado pelo /escanear:
import { useScanProva } from "@/hooks/useScanProva";
// Retorna scan.transicoes_permitidas + motivo_obrigatorio_em
```

Os endpoints `POST /scan` + `POST /{id}/transicoes` já fazem todo o roteamento v3.0/v4.0 internamente (Wave 3 v4.0 / C11).

### 7.2 Filtros de visibilidade

`useAuthorization` da Wave 1 v4.0 já faz checagem por chave (provas.detail, provas.cancel, etc.). C12 herda da página de detalhe — não precisa duplicar.

---

## 8. Decisões fixadas no Gate 1 do C11 que afetam o C12

| ID | Decisão | Impacto no C12 |
|---|---|---|
| M-1 | Ator de "Filial.CRIADA → ENCAMINHADA_PARA_O_VENDEDOR" = Vendedor | Renderize a primeira etapa da rota Filial como "Vendedor" |
| M-2b(a) | `COM_MOTORISTA` legacy ≠ `COM_MOTORISTA_ENTREGA_FINAL` v4.0 (valores distintos) | Renderize ambos como "Entrega final" no label, mas o status técnico distingue |
| M-5 | Contexto do motorista derivado de `status_novo` (não persistido em coluna) | Use o helper `contextoMotorista(status)` |
| M-7 | Mensagens de erro em voz ativa concisa | Se C12 exibir erros, use o mesmo tom |

---

## 9. Testes de regressão recomendados para o C12

- [ ] Timeline renderiza corretamente para cada uma das 4 rotas v4.0 (Matriz, Lam. Matriz, Filial, Lam. Filial).
- [ ] Timeline renderiza prova legacy (rota=NULL) sem quebrar.
- [ ] Etapa atual destacada conforme `prova.status`.
- [ ] Cancelamento visual aparece quando `prova.status === "CANCELADA"` + `prova.motivo_cancelamento` exibido.
- [ ] Reprovação mostra motivo + indica início de novo ciclo.
- [ ] Múltiplos ciclos renderizados com separador.
- [ ] 3 contextos do motorista identificáveis visualmente (badge ou ícone distinto).
- [ ] `prefers-reduced-motion` degrada animações.
- [ ] Acessibilidade: navegação por teclado funciona; leitor de tela anuncia etapas.

---

## 10. Arquivos que C12 PODE tocar sem fricção

- `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` — refactor permitido.
- `frontend/src/app/(dashboard)/provas/[id]/timeline.module.css` — refactor permitido.
- `frontend/src/lib/types/prova.ts` — apenas adicionar `ROTA_ETAPAS` ou `STATUS_METADATA`. Não mudar tipos existentes.

## 11. Arquivos que C12 NÃO DEVE tocar

- `backend/app/state_machine/` — máquina de estados é responsabilidade do C11.
- `backend/migrations/` — banco já está estável.
- `frontend/src/app/(dashboard)/provas/[id]/AdminActions.tsx` — ações admin já corretas para v4.0.
- `frontend/src/app/(dashboard)/escanear/` — scanner já funciona com v4.0.

---

**Fim do contrato.** Qualquer dúvida que não esteja resolvida aqui é gap a documentar para uma futura iteração.
