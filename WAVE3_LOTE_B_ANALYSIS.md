# Wave 3 — Lote B — Analysis (Componente 12)

**Escopo:** Componente 12 — Timeline Visual de Estagios.
**Data:** 2026-04-13.
**Status:** Aguardando GO LOTE B.

---

## 1. Escopo exato do Componente 12

### Backlog v3.0

> **C12 — Timeline Visual de Estagios**
> Framer Motion, ramificacao de rotas, indicacao de reprovacao, responsavel e timestamp por etapa.
> Prioridade: Must Have. Depende de: C11.

### Requisito funcional

> **RF-011** — O sistema deve exibir uma timeline visual para cada prova, indicando
> claramente: os estagios percorridos, a rota seguida (padrao ou direta), eventuais
> reprovacoes com motivo, o responsavel e o timestamp de cada etapa.

### Historia de usuario

> **US-011** — Como usuario da 3Studio, eu quero visualizar a timeline completa de
> uma prova para saber em que etapa e com quem ela esta.

### Criterios de aceitacao (US-011)

| # | Criterio | Como sera atendido |
|---|---|---|
| 1 | A timeline exibe todos os estagios percorridos, incluindo ramificacoes | Cada movimentacao vira um no visual conectado; rota padrao e direta renderizadas com caminhos distintos |
| 2 | Cada etapa concluida mostra responsavel e data/hora | Cada no exibe `usuario_nome`, `usuario_setor` e `created_at` formatado com data + hora |
| 3 | Reprovacoes sao exibidas com motivo e destaque visual | Nos de reprovacao recebem borda/fundo `--color-danger`, com callout do `motivo_reprovacao` |
| 4 | A rota seguida (padrao ou direta) e indicada | Badge de rota exibido no no da `APROVADA_PELO_VENDEDOR` (momento em que a rota e determinada) |
| 5 | A etapa atual e destacada visualmente | Ultimo no (status atual) recebe borda `--color-accent` + indicador pulsante via Framer Motion |

### Definition of Done (global, Backlog v3.0)

| # | Criterio | Aplicabilidade ao C12 |
|---|---|---|
| 1 | Code review | Revisao pelo Mario durante iteracoes |
| 2 | Testes unitarios >= 80% cobertura | Logica de transformacao de dados (pure function) testavel; cobertura frontend via tsc + lint + build |
| 3 | Testes de integracao passando | 389 testes backend permanecem verdes (zero mudanca backend) |
| 4 | Migrations aplicadas e versionadas | N/A — zero migrations (100% frontend) |
| 5 | Validada contra criterios US-011 | 5 criterios acima verificados via preview tools |
| 6 | Sem erros no console/logs | `preview_console_logs` limpo, `preview_logs` limpo |
| 7 | Documentacao atualizada | CHANGELOG, DECISIONS (se houver ADR), CLAUDE.md |
| 8 | Policies RLS versionadas | N/A — zero mudancas RLS |

---

## 2. Interface com Lote A — consumido sem modificacao

| Contrato Lote A | Tipo | Consumo no C12 |
|---|---|---|
| `GET /api/v1/provas/{id}/movimentacoes` | Endpoint | Fonte de dados da timeline (ja chamado pelo `useProvaDetail`) |
| `MovimentacaoResponse` | Tipo TS | Dados de cada no: `status_anterior`, `status_novo`, `usuario_nome`, `usuario_setor`, `motivo_reprovacao`, `ciclo`, `rota_no_momento`, `created_at` |
| `MovimentacaoListResponse` | Tipo TS | Wrapper `{ items, total }` retornado pelo endpoint |
| `ProvaResponse.rota` | Campo | Rota efetiva (populada na APROVADA); indica rota seguida |
| `ProvaResponse.status` | Campo | Status atual da prova — determina qual no e "atual" |
| `ProvaResponse.ciclo_atual` | Campo | Ciclo corrente — usado para agrupar e separar ciclos |
| `useProvaDetail` hook | Hook React | Ja carrega `movimentacoes` em paralelo via `Promise.allSettled` |
| `STATUS_LABELS`, `ROTA_LABELS` | Constantes | Labels pt-BR dos nos e badges de rota |
| `executar_transicao` (state_machine) | Servico backend | Nao consumido diretamente — mas gera os dados que a timeline exibe |
| Placeholder `timelineCard` (page.tsx:250-291) | JSX | **Substituido** pelo componente Timeline visual |

**Compromisso:** nenhum desses contratos sera alterado. O `useProvaDetail` continua retornando
os mesmos tipos. O endpoint `/movimentacoes` nao muda. Os tipos TS permanecem intactos.

---

## 3. Interface com Waves 0/1/2 — consumido sem modificar

| Recurso | Wave | Consumo no C12 |
|---|---|---|
| `globals.css` custom properties | Wave 1 | Design tokens: `--color-accent`, `--color-danger`, `--color-success`, `--color-bg-surface-2`, `--color-text-*` |
| `detalhe.module.css` | Wave 2 C08 | Estilos existentes do `timelineCard` (fundo preto, titulo, empty state) **preservados e estendidos** |
| `provas/[id]/page.tsx` | Wave 2 C08 | Unica alteracao: substituir o bloco `<ul className={styles.timelineList}>` pelo componente `<Timeline>` |
| `lib/types/prova.ts` | Wave 2 | Tipos `StatusProva`, `Rota`, `Setor`, `MovimentacaoResponse` consumidos sem alteracao |
| Layout dashboard (`layout.tsx`) | Wave 1 | Zero alteracao |
| Supabase Auth / JWT | Wave 1 | Nao tocado — token ja injetado pelo `useProvaDetail` |
| CSS Modules pattern | Wave 1 | Seguido — zero CSS global, zero Tailwind |

---

## 4. Contratos a expor para o Lote C

O Componente 12 (Timeline) e um componente de **leitura/visualizacao** — nao gera dados, apenas
renderiza os que ja existem. Os contratos para o Lote C sao passivos:

| Contrato | Para quem | Descricao |
|---|---|---|
| `<Timeline>` renderiza `CANCELADA` corretamente | C13 | Quando C13 implementar cancelamento, a timeline exibira a movimentacao de cancelamento com estilo visual distinto (cinza/riscado), sem necessidade de alterar o componente |
| `<Timeline>` renderiza ciclos multiplos | C14 | Quando C14 implementar reinicio de ciclo (`ciclo_atual` incrementado), a timeline agrupa movimentacoes por ciclo com separador visual, sem alteracao |
| `<Timeline>` aceita `movimentacoes` como prop | C13/C14 | Os endpoints de cancelamento/reinicio retornam `ProvaResponse` atualizado; o `useProvaDetail.reload()` refaz o fetch e a timeline re-renderiza automaticamente |
| Estilo `timelineNodeCancelada` preparado | C13 | Classe CSS para no de cancelamento (fundo cinza, icone X) ja definida no CSS Module, mesmo que C13 nao exista ainda |

**Principio:** o componente Timeline trata TODOS os 10 status do enum `StatusProva` visualmente,
incluindo `CANCELADA` e `REPROVADA_PELO_VENDEDOR`. Se C13/C14 gerarem novas movimentacoes com
esses status, a timeline renderiza sem mudanca de codigo.

---

## 5. Modelo de dados

**Nenhuma alteracao no banco de dados.**

- Zero tabelas novas.
- Zero colunas novas.
- Zero migrations Alembic.
- Zero politicas RLS.
- Zero indexes.
- `alembic_version` permanece `009`.

O Componente 12 consome exclusivamente dados ja existentes:
- `movimentacoes` (via `GET /{id}/movimentacoes`)
- `provas_digitais.status`, `provas_digitais.rota`, `provas_digitais.ciclo_atual`

### Modelo de dados frontend (transformacao para renderizacao)

```typescript
/** No visual da timeline — derivado de MovimentacaoResponse + contexto da prova. */
interface TimelineNode {
  id: string;                       // movimentacao.id
  statusAnterior: StatusProva;      // de onde veio
  statusNovo: StatusProva;          // para onde foi
  usuarioNome: string;              // quem executou
  usuarioSetor: Setor;              // setor do ator
  motivoReprovacao: string | null;  // motivo (se reprovacao)
  ciclo: number;                    // ciclo desta movimentacao
  rotaNoMomento: Rota | null;      // rota no momento da transicao
  createdAt: string;                // timestamp ISO
  isCurrent: boolean;               // e o ultimo no (status atual)?
  isReprovacao: boolean;            // status_novo contém REPROVADA?
  isCancelamento: boolean;          // status_novo === CANCELADA?
  isRoteamento: boolean;            // status_novo === APROVADA (momento que rota e definida)?
}
```

Funcao pura `buildTimelineNodes(movimentacoes, prova) -> TimelineNode[]` faz a
transformacao — testavel sem DOM.

---

## 6. Contratos de API

**Nenhum endpoint novo. Nenhum endpoint modificado.**

O C12 consome apenas:

| Endpoint | Metodo | Resposta | RBAC | Ja existente? |
|---|---|---|---|---|
| `/api/v1/provas/{id}` | GET | `ProvaResponse` | Scoping por perfil (Wave 2) | Sim (Wave 2 C08) |
| `/api/v1/provas/{id}/movimentacoes` | GET | `MovimentacaoListResponse` | Scoping por perfil (Wave 2) | Sim (Wave 2 C08) |

Ambos ja sao chamados pelo `useProvaDetail` hook. Zero trabalho backend.

---

## 7. Impacto no frontend

### 7.1 Nova dependencia

| Pacote | Versao | Motivo | Referencia |
|---|---|---|---|
| `framer-motion` | `^11` (latest) | Animacoes da timeline (stagger entrance, pulse no atual) | DAT v2.0 lista como lib de animacao |

### 7.2 Arquivos novos

| Arquivo | Descricao |
|---|---|
| `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` | Componente visual da timeline (extraido da page.tsx) |
| `frontend/src/app/(dashboard)/provas/[id]/timeline.module.css` | CSS Module dedicado para a timeline visual |

### 7.3 Arquivos modificados

| Arquivo | Alteracao |
|---|---|
| `frontend/src/app/(dashboard)/provas/[id]/page.tsx` | Substituir bloco `timelineCard` (linhas ~250-291) por `<Timeline movimentacoes={movimentacoes} prova={prova} />`. Remove estilos de timeline do import |
| `frontend/src/app/(dashboard)/provas/[id]/detalhe.module.css` | **Remover** classes `timelineList`, `timelineItem`, `timelineHeader`, `timelineStatus`, `timelineDate`, `timelineMeta`, `timelineMotivo` (movidas para `timeline.module.css`). **Preservar** `timelineCard`, `timelineTitle`, `timelineEmpty`, `timelineHint` (container preto continua na page) |
| `frontend/package.json` | +1 dependencia (`framer-motion`) |
| `frontend/package-lock.json` | Atualizado via `npm install` |

### 7.4 Arquivos NAO tocados (zero impacto)

- `page.tsx` fora do bloco timeline (dados, arte, breadcrumb, modal) — intocado
- `VisualizarEtiquetaModal.tsx` — intocado
- `useProvaDetail.ts` — intocado
- `lib/types/prova.ts` — intocado
- `hooks/useScanner.ts`, `useScanProva.ts`, `useExecutarTransicao.ts` — intocados
- `escanear/page.tsx` — intocado
- Layout, login, usuarios, nova-prova, provas (listagem), configuracoes — intocados
- Todo o backend — intocado

### 7.5 Design visual

A timeline fica **dentro do card preto** (`timelineCard`) que ja existe na pagina de detalhe.
O container preto e preservado — apenas seu conteudo interno muda.

**Estrutura visual:**

```
┌──────────────────────────────────────┐
│  Card branco (innerCard)             │
│  ┌──────────────┐ ┌──────────────┐  │
│  │ Dados prova  │ │  Arte (img)  │  │
│  └──────────────┘ └──────────────┘  │
│  ┌──────────────────────────────────┐│
│  │  Card preto (timelineCard)       ││
│  │  ┌ Ciclo 1 ───────────────────┐ ││
│  │  │ ● Criada                   │ ││
│  │  │ │                          │ ││
│  │  │ ● Retirada pelo vendedor   │ ││
│  │  │ │                          │ ││
│  │  │ ● Aprovada [Rota: Padrao]  │ ││
│  │  │ │                          │ ││
│  │  │ ● De volta a 3Studio       │ ││
│  │  │ │                          │ ││
│  │  │ ◉ Com motorista ← ATUAL   │ ││
│  │  └────────────────────────────┘ ││
│  └──────────────────────────────────┘│
└──────────────────────────────────────┘
```

**Mapeamento visual por tipo de no:**

| Tipo de no | Indicador | Cor da borda | Detalhe extra |
|---|---|---|---|
| Etapa concluida | `●` (circulo preenchido) | `--color-accent` (amarelo) | usuario + data/hora |
| Etapa atual | `◉` (circulo duplo, pulsa) | `--color-accent` animado | usuario + data/hora + label "Atual" |
| Reprovacao | `●` (circulo preenchido) | `--color-danger` (vermelho) | motivo em callout vermelho |
| Cancelamento | `✕` (x) | cinza `#575757` | motivo em callout cinza |
| Roteamento | Badge no no | accent | Badge "Rota padrao" ou "Rota direta" |

**Ciclos multiplos:** quando `ciclo > 1`, os nos sao agrupados com um separador visual:

```
  ┌ Ciclo 1 ────────────────┐
  │ ● Criada                 │
  │ ● Retirada               │
  │ ● Reprovada (motivo: ..) │
  └──────────────────────────┘
  ┌ Ciclo 2 ────────────────┐
  │ ● Criada (reiniciada)    │
  │ ● Retirada               │
  │ ◉ Aprovada ← ATUAL      │
  └──────────────────────────┘
```

### 7.6 Supabase Realtime

Nao aplicavel ao C12. O Realtime sera introduzido na Wave 4 (Dashboard). A timeline
atualiza via `useProvaDetail.reload()` quando o usuario navega para a pagina — pull model,
nao push.

---

## 8. Storage R2

**Nao aplicavel.** O C12 nao interage com o Cloudflare R2. Nenhum upload, download ou
presigned URL novo.

---

## 9. Plano de testes

### 9.1 Camada 1 — Unitarios (logica pura)

| Teste | Descricao | Arquivo |
|---|---|---|
| `buildTimelineNodes` com 0 movimentacoes | Retorna array vazio | Inline no componente ou funcao exportada testavel |
| `buildTimelineNodes` com rota padrao completa | 6 nos, ultimo `isCurrent=true`, no APROVADA tem `isRoteamento=true` | Idem |
| `buildTimelineNodes` com rota direta | 4 nos (sem DE_VOLTA, COM_MOTORISTA, ENVIADA) | Idem |
| `buildTimelineNodes` com reprovacao | No REPROVADA tem `isReprovacao=true` + motivo | Idem |
| `buildTimelineNodes` com 2 ciclos | Agrupamento correto, ultimo ciclo tem `isCurrent` | Idem |
| `buildTimelineNodes` com cancelamento | No CANCELADA tem `isCancelamento=true` | Idem |

**Nota:** como o projeto nao tem framework de teste frontend (Jest/Vitest), esses testes
podem ser validados de duas formas:
- **(A)** Extrair `buildTimelineNodes` como funcao pura e testar via um script Node inline.
- **(B)** Validar visualmente via preview tools com cenarios mockados.
- **(C)** Adicionar ao backend como teste de contrato (verificar que o tipo retornado pelo endpoint
  pode ser transformado). Overengineering para C12 — registrar como TODO Wave 6.

**Recomendacao:** opcao (B) — validacao visual via preview + TypeScript strict como rede de
seguranca. O projeto nao tem test runner frontend e adicioná-lo nao faz parte do C12.

### 9.2 Camada 2 — Integracao backend

**Zero testes novos no backend.** Os 389 testes existentes devem continuar passando (regressao zero).

Validacao: `cd backend && .venv/Scripts/python -m pytest --tb=short -q` → 389 passed.

### 9.3 Camada 3 — E2E / Visual

| Cenario | Metodo de verificacao |
|---|---|
| Prova sem movimentacoes | `preview_snapshot` → texto "Esta prova ainda nao teve movimentacoes" |
| Prova com 1+ movimentacoes (rota padrao) | `preview_screenshot` → nos conectados, rota badge |
| Prova com reprovacao | `preview_screenshot` → no vermelho com motivo |
| Prova com 2 ciclos | `preview_screenshot` → separador de ciclo |
| Prova cancelada | `preview_screenshot` → no cinza |
| Animacoes Framer Motion | `preview_screenshot` apos load → nos visiveis (stagger) |
| Responsivo (< 1100px) | `preview_resize` → timeline empilha corretamente |
| Zero erros console | `preview_console_logs` → vazio |
| Zero erros servidor | `preview_logs` → vazio |
| Build limpo | `next build` → OK |
| TypeScript limpo | `tsc --noEmit` → 0 erros |
| ESLint limpo | `next lint` → 0 warnings |

---

## 10. Riscos e pontos de atencao

| # | Risco | Probabilidade | Impacto | Mitigacao |
|---|---|---|---|---|
| R1 | Framer Motion aumenta bundle size | Media | Baixo | framer-motion v11 suporta tree-shaking. Importar apenas `motion` e `AnimatePresence`. Verificar bundle com `next build` |
| R2 | 0 movimentacoes em producao (smoke com camera nao feito) | Alta | Baixo | Timeline ja trata empty state. Usar dados mockados via preview_eval para visualizar cenarios |
| R3 | `html5-qrcode` conflita com framer-motion em imports SSR | Baixa | Medio | Framer Motion suporta SSR nativamente. `useScanner` ja faz lazy import — nao ha conflito |
| R4 | CSS de timeline no card preto pode conflitar com estilos existentes | Baixa | Baixo | CSS Module isolado (`timeline.module.css`). Zero classes globais |
| R5 | Performance com muitas movimentacoes (>50 nos) | Muito baixa | Baixo | Volume esperado: ~10-15 nos por prova (pior caso: 3 ciclos × 7 etapas = 21). Framer Motion com `layout` desligado |
| R6 | Upgrade framer-motion pode ter breaking changes futuras | Baixa | Baixo | Pinar `^11` (major lock). Upgrade sera tratado na Wave 6 |

**Limites de free tier:** nenhum impacto. O C12 nao adiciona chamadas de API, nao usa storage,
nao gera carga extra no banco. A unica adição e ~30-50 KB de bundle JS (framer-motion tree-shaken).

---

## 11. Sub-blocos de implementacao

### Bloco B.1 — Framer Motion + Componente Timeline + Integracao

**Escopo:** instalar Framer Motion, criar o componente `Timeline.tsx` com a funcao de
transformacao de dados, o layout visual completo (nos, linhas, badges, agrupamento por ciclo),
animacoes Framer Motion, e integrar na `page.tsx` substituindo o placeholder.

**Entregaveis:**
- `npm install framer-motion`
- `frontend/src/app/(dashboard)/provas/[id]/Timeline.tsx` — componente completo:
  - Funcao pura `buildTimelineNodes()` (transformacao de dados)
  - Renderizacao visual: nos verticais conectados por linha
  - Badge de rota no no APROVADA
  - Destaque de reprovacao (vermelho + motivo)
  - Destaque do no atual (accent + indicador pulsante)
  - Agrupamento por ciclo com separador
  - Tratamento de cancelamento (cinza)
  - Animacoes: staggered entrance dos nos via `motion.div`
- `frontend/src/app/(dashboard)/provas/[id]/timeline.module.css` — estilos visuais
- `page.tsx` — substituir bloco placeholder (linhas ~250-291) por `<Timeline>`
- `detalhe.module.css` — remover classes de timeline antigas (agora em `timeline.module.css`)

**Validacao:**
- `tsc --noEmit` limpo
- `next lint` limpo
- `next build` OK
- Preview visual com dados mockados (via `preview_eval` injetando movimentacoes)

### Bloco B.2 — Verificacao Visual + Documentacao + Closeout

**Escopo:** verificacao completa via preview tools, ajustes de responsividade, documentacao
final e closeout do Lote B.

**Entregaveis:**
- Verificacao dos 5 criterios US-011 via preview tools
- Ajustes de CSS responsivo (< 1100px, < 768px)
- Edge cases visuais: empty, cancelada, multi-ciclo, reprovacao
- `CHANGELOG.md` — entrada do Lote B
- `DECISIONS.md` — ADR se houver decisao tecnica relevante
- `CLAUDE.md` — atualizacao minima (Wave 3 status)
- `WAVE3_LOTE_B_CLOSEOUT.md` — DoD completo, cobertura, contratos para Lote C
- `pytest --tb=short -q` no backend → 389 passed (regressao zero)
- Screenshots de prova via preview tools

---

## Resumo de impacto

| Dimensao | C12 |
|---|---|
| Backend | **Zero** alteracoes |
| Banco de dados | **Zero** alteracoes |
| RLS | **Zero** alteracoes |
| Alembic | **Zero** migrations |
| R2 Storage | **Zero** uso |
| Frontend — arquivos novos | 2 (`Timeline.tsx` + `timeline.module.css`) |
| Frontend — arquivos modificados | 3 (`page.tsx`, `detalhe.module.css`, `package.json`) |
| Frontend — deps novas | 1 (`framer-motion`) |
| Testes backend novos | 0 |
| Sub-blocos | 2 (B.1 componente + B.2 verificacao/closeout) |
