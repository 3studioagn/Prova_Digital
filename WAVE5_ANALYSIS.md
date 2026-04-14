# WAVE5_ANALYSIS.md — Relatorios Gerenciais + Exportacao CSV

**Wave:** 5
**Componente:** 16 — Relatorios Gerenciais
**Prioridade:** Should Have
**Dependencias:** Componente 12 (Wave 3, timeline) + Componente 15 (Wave 4, dashboard)
**Data:** 2026-04-14

> **C17 (Atalhos Rapidos):** Mario confirmou que os atalhos ja existentes no dashboard
> (Escanear QR Code + Nova Prova) atendem ao RF-016. Nenhum trabalho adicional em C17.

---

## 1. Escopo Exato (extraido do Backlog v3.0 + Requisitos v3.0)

### Componente 16 — Relatorios Gerenciais

**Descricao (Backlog):** Tempo medio de aprovacao, provas por vendedor, atrasadas, taxa de
reprovacao, distribuicao por rota, exportacao CSV.

**Requisitos vinculados:**

| Req | Descricao | Prioridade |
|-----|-----------|------------|
| RF-015 | Secao de relatorios contendo: tempo medio de aprovacao, total de provas por vendedor, quantidade de provas atrasadas, total geral de provas, taxa de reprovacao por vendedor e exportacao dos dados em formato CSV. | Should |
| US-014 | "Como usuario da 3Studio, eu quero acessar relatorios de tempo medio de aprovacao, provas atrasadas e taxa de reprovacao para identificar gargalos no fluxo." | — |
| RN-008 | Prova "Atrasada" = mesma status por mais tempo que o configurado (padrao 48h). | Must |
| RNF-001 | Dashboard e listagem carregam em < 3s com ate 30 usuarios simultaneos. | Must |

### Criterios de Aceitacao (US-014)

1. O relatorio exibe tempo medio por vendedor e geral.
2. Provas atrasadas sao listadas com dias de atraso.
3. Taxa de reprovacao por vendedor e exibida.
4. E possivel exportar os dados em formato CSV.

### Definition of Done (DoD Global do Backlog)

1. Code review.
2. Testes unitarios >= 80% em logica de negocio.
3. Testes de integracao passando.
4. Migrations versionadas e documentadas.
5. Funcionalidade validada contra criterios de aceitacao.
6. Sem erros no console/backend.
7. Documentacao interna atualizada.
8. Politicas RLS verificadas e versionadas.

---

## 2. Mapa de Dependencias com Waves 0/1/2/3/4

A Wave 5 **consome** os seguintes artefatos sem modifica-los:

| Artefato | Wave | Uso na Wave 5 |
|----------|------|---------------|
| `provas_digitais` (tabela, 13 registros) | 0 | Fonte de dados: status, rota, vendedor_id, created_at |
| `movimentacoes` (tabela, 8 registros) | 0 | Calculo de tempo medio de aprovacao + ultima movimentacao para atraso |
| `usuarios` (tabela, 3 registros) | 0 | JOIN para nome do vendedor nos relatorios |
| `configuracoes_sistema.tempo_atraso_horas_uteis` | 0+2 | Parametro de atraso (RN-008) — reuso identico a Wave 4 |
| `StatusProvaEnum`, `RotaEnum` | 0 | Mapeamento de status e rota nos relatorios |
| `_scoping_filter(user)` | 2 | Scoping dos relatorios por perfil (admin ve tudo) |
| `GET /api/v1/provas/` (filtros C07) | 2 | Padrao de filtro por periodo reutilizado |
| `get_admin_user` dependency | 1 | RBAC: relatorios sao admin-only (BACKLOG C05) |
| `apiFetch` wrapper | 1 | Chamadas ao backend |
| `framer-motion` | 3 | Animacoes de entrada (reuso da dep existente) |
| Design tokens (`globals.css`) | 1 | Tokens de cores, radius, tipografia |
| Calculo de "atrasadas" (query Wave 4) | 4 | Reuso parcial — Wave 5 precisa listar provas, nao so contar |
| Cache TTL 5s do dashboard (ADR-092) | 4 | NAO reutilizado — relatorios nao precisam de cache (acesso esporadico) |

**Nenhum artefato de waves anteriores sera modificado**, exceto:
- `layout.tsx`: ativar `href: "/relatorios"` no item de menu existente (1 palavra, padrao identico a `/dashboard` e `/escanear`).

---

## 3. Modelo de Dados

### Novas tabelas: NENHUMA

Todos os indicadores do RF-015 sao **derivados por query** das tabelas existentes:
- `provas_digitais` (status, rota, vendedor_id, created_at)
- `movimentacoes` (status_anterior, status_novo, created_at, prova_id)
- `usuarios` (nome, setor, localizacao)

Volume atual (13 provas) e projetado (< 500) nao justifica materialized views ou tabelas de agregacao.

### Novas colunas: NENHUMA

### Novos indexes: NENHUM

Os indexes existentes ja cobrem as queries necessarias:
- `idx_provas_vendedor` — GROUP BY vendedor_id
- `idx_provas_status` — filtro por status
- `idx_provas_status_created` — filtro composto status + periodo
- `idx_provas_created_at` — filtro por periodo
- `idx_movimentacoes_prova_data` — (prova_id, created_at DESC) para ultima movimentacao e tempo medio

### Novas policies RLS: NENHUMA

O endpoint de relatorios usara `service_role` (como todos os outros) e aplicara restricao via `get_admin_user` na camada de aplicacao. Relatorios sao admin-only conforme BACKLOG C05.

### Alteracao de infraestrutura: NENHUMA

Sem migrations Alembic, sem alteracoes de Realtime, sem novas policies.

---

## 4. Contratos de API

### Endpoint 1: `GET /api/v1/provas/relatorios`

**Objetivo:** Retornar metricas agregadas para a pagina de relatorios.

**RBAC:** Somente `get_admin_user` (is_admin=true). Vendedor, Motorista e Clicheria recebem 403.

**Justificativa do RBAC:** O BACKLOG C05 diz "Impede que um vendedor [...] acesse relatorios."
A US-014 diz "Como usuario da 3Studio [Administrador]..."

```
GET /api/v1/provas/relatorios?inicio=2026-04-01&fim=2026-04-14
Authorization: Bearer <jwt>

Query params (todos opcionais):
  inicio    date (YYYY-MM-DD)  Inicio do periodo (inclusivo). Default: 30 dias atras.
  fim       date (YYYY-MM-DD)  Fim do periodo (inclusivo). Default: hoje.

Response 200:
{
  "periodo": {
    "inicio": "2026-04-01",
    "fim": "2026-04-14"
  },
  "total_geral": 13,
  "tempo_medio_aprovacao_horas": 4.5,
  "total_atrasadas": 2,
  "distribuicao_por_rota": {
    "PADRAO": 8,
    "DIRETA": 3,
    "SEM_ROTA": 2
  },
  "por_vendedor": [
    {
      "vendedor_id": "uuid",
      "vendedor_nome": "Mario Souza",
      "vendedor_localizacao": "FILIAL",
      "total_provas": 5,
      "aprovadas": 3,
      "reprovadas": 1,
      "taxa_reprovacao_pct": 20.0,
      "tempo_medio_aprovacao_horas": 3.2
    }
  ],
  "atrasadas": [
    {
      "prova_id": "uuid",
      "nome": "Arte XYZ",
      "nro_requerimento": "REQ-001",
      "cliente": "Cliente A",
      "vendedor_nome": "Mario Souza",
      "status": "RETIRADA_PELO_VENDEDOR",
      "rota": "PADRAO",
      "dias_atraso": 3.5,
      "ultima_movimentacao_em": "2026-04-10T14:30:00Z"
    }
  ],
  "atualizado_em": "2026-04-14T15:30:00Z"
}
```

**Detalhamento dos indicadores RF-015:**

| Indicador | Calculo SQL | Notas |
|-----------|-------------|-------|
| `total_geral` | `COUNT(*)` de provas no periodo (por `created_at`) | Todas as provas, qualquer status |
| `tempo_medio_aprovacao_horas` | AVG do intervalo entre `status_novo = APROVADA_PELO_VENDEDOR` e `status_anterior = RETIRADA_PELO_VENDEDOR` na mesma prova, usando `movimentacoes.created_at` | Apenas provas que foram aprovadas. Horas corridas (consistente com ADR-091 Wave 4). NULL se nenhuma aprovacao no periodo. |
| `total_atrasadas` | COUNT de provas ativas cujo `tempo_desde_ultima_mov > tempo_atraso_horas` | Reuso do calculo RN-008 (Wave 4). Cross-period — nao depende de `inicio/fim`. |
| `distribuicao_por_rota` | `COUNT(*) GROUP BY rota` | `SEM_ROTA` = provas com `rota IS NULL` (status CRIADA ou RETIRADA, rota ainda nao determinada) |
| `por_vendedor[].total_provas` | `COUNT(*) GROUP BY vendedor_id` no periodo | |
| `por_vendedor[].aprovadas` | COUNT de provas com pelo menos 1 movimentacao `status_novo = APROVADA_PELO_VENDEDOR` | No periodo de criacao da prova |
| `por_vendedor[].reprovadas` | COUNT de provas com pelo menos 1 movimentacao `status_novo = REPROVADA_PELO_VENDEDOR` | Idem. Uma prova pode ter sido aprovada E reprovada em ciclos diferentes. |
| `por_vendedor[].taxa_reprovacao_pct` | `(reprovadas / total_provas) * 100` | Arredondado a 1 casa decimal. 0.0 se total_provas = 0. |
| `por_vendedor[].tempo_medio_aprovacao_horas` | AVG do intervalo RETIRADA→APROVADA para provas daquele vendedor | Horas corridas. NULL se nenhuma aprovacao. |
| `atrasadas[]` | Lista de provas ativas com atraso, ordenada por `dias_atraso DESC` | US-014: "listadas com dias de atraso" |

**Codigos HTTP:**

| Codigo | Cenario |
|--------|---------|
| 200 | Relatorios retornados |
| 401 | Sem autenticacao |
| 403 | Usuario nao e admin |
| 422 | Periodo invalido (inicio > fim, datas mal-formadas) |
| 502 | Erro de banco de dados |

### Endpoint 2: `GET /api/v1/provas/relatorios/csv`

**Objetivo:** Exportar dados das provas em formato CSV para analise externa.

**RBAC:** Somente `get_admin_user`.

```
GET /api/v1/provas/relatorios/csv?inicio=2026-04-01&fim=2026-04-14
Authorization: Bearer <jwt>

Response 200:
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="relatorio_provas_2026-04-01_2026-04-14.csv"

nome,nro_requerimento,cliente,vendedor_nome,vendedor_localizacao,status,rota,ciclo_atual,criada_em,ultima_movimentacao_em,dias_desde_ultima_mov,aprovada,reprovada
"Arte XYZ","REQ-001","Cliente A","Mario Souza","FILIAL","APROVADA_PELO_VENDEDOR","DIRETA",1,"2026-04-10 08:00","2026-04-10 11:30",0.15,true,false
```

**Colunas do CSV:**

| Coluna | Origem | Nota |
|--------|--------|------|
| `nome` | `provas_digitais.nome` | |
| `nro_requerimento` | `provas_digitais.nro_requerimento` | |
| `cliente` | `provas_digitais.cliente` | |
| `vendedor_nome` | `usuarios.nome` (JOIN) | |
| `vendedor_localizacao` | `usuarios.localizacao` (JOIN) | MATRIZ, FILIAL ou vazio |
| `status` | `provas_digitais.status` | Label legivel (STATUS_LABELS) |
| `rota` | `provas_digitais.rota` | PADRAO, DIRETA ou vazio |
| `ciclo_atual` | `provas_digitais.ciclo_atual` | |
| `criada_em` | `provas_digitais.created_at` | Formato BRT: YYYY-MM-DD HH:MM |
| `ultima_movimentacao_em` | MAX(movimentacoes.created_at) ou created_at | Formato BRT |
| `dias_desde_ultima_mov` | Calculado | Arredondado a 2 casas |
| `aprovada` | Boolean | true se teve APROVADA_PELO_VENDEDOR |
| `reprovada` | Boolean | true se teve REPROVADA_PELO_VENDEDOR |

**Implementacao:** `StreamingResponse` do FastAPI com `io.StringIO` + `csv.writer`.
Sem limite de paginacao — exporta todas as provas do periodo. Volume maximo esperado: < 500 linhas.

**Codigos HTTP:** Identicos ao endpoint JSON (200, 401, 403, 422, 502).

### Pydantic Schemas

```python
# backend/app/domain/schemas/relatorio.py

class PeriodoFiltro(BaseModel):
    inicio: date
    fim: date

    @model_validator(mode="after")
    def inicio_antes_fim(self) -> "PeriodoFiltro":
        if self.inicio > self.fim:
            raise ValueError("inicio deve ser anterior ou igual a fim")
        return self

class VendedorRelatorio(BaseModel):
    vendedor_id: UUID
    vendedor_nome: str
    vendedor_localizacao: str | None
    total_provas: int
    aprovadas: int
    reprovadas: int
    taxa_reprovacao_pct: float
    tempo_medio_aprovacao_horas: float | None

class ProvaAtrasada(BaseModel):
    prova_id: UUID
    nome: str
    nro_requerimento: str
    cliente: str
    vendedor_nome: str
    status: str
    rota: str | None
    dias_atraso: float
    ultima_movimentacao_em: datetime

class DistribuicaoRota(BaseModel):
    PADRAO: int = 0
    DIRETA: int = 0
    SEM_ROTA: int = 0

class StatusCount(BaseModel):
    status: str
    label: str
    quantidade: int

class RelatorioResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    periodo: PeriodoFiltro
    total_geral: int
    tempo_medio_aprovacao_horas: float | None
    total_atrasadas: int
    distribuicao_por_rota: DistribuicaoRota
    distribuicao_por_status: list[StatusCount]   # PieChart: provas ativas por status
    por_vendedor: list[VendedorRelatorio]
    atrasadas: list[ProvaAtrasada]
    atualizado_em: datetime
```

---

## 5. Impacto no Frontend

### Rota Next.js nova: `/relatorios`

```
frontend/src/app/(dashboard)/relatorios/
  ├── page.tsx                 # Pagina principal dos relatorios
  └── relatorios.module.css    # CSS Module dedicado
```

### Layout da pagina

Sem design Figma especificado para relatorios. Layout proposto segue os padroes visuais
estabelecidos nas Waves 2-4 (cards brancos com `border-radius: 31px`, tokens de `globals.css`):

```
┌─────────────────────────────────────────────────────────┐
│  Filtro de periodo: [Inicio] [Fim] [Aplicar]  [CSV ↓]  │
├──────────┬──────────┬───────────┬───────────────────────┤
│  Total   │  Tempo   │  Taxa     │  Distribuicao         │
│  Geral   │  Medio   │  Reprov.  │  por Rota             │
│  13      │  4.5h    │  15.3%    │  Padrao: 8 | Direta:3 │
├──────────────────┬──────────────────┬───────────────────┤
│ ● Provas Ativas  │ █ Tempo Medio    │ █ Top Vendedores  │
│   (PieChart)     │   por Vendedor   │   por Volume      │
│   Com Vend: 3    │   (BarChart)     │   (BarChart)      │
│   Aprovadas: 2   │   Mario: 3.2h   │   Mario: 5        │
│   ...            │   Ana: 5.1h     │   Ana: 3          │
├──────────────────┴──────────────────┴───────────────────┤
│  Metricas por Vendedor                                  │
│  ┌─────────┬───────┬──────┬────────┬──────┬──────────┐  │
│  │Vendedor │Total  │Aprov.│Reprov. │Taxa% │Tempo Med │  │
│  ├─────────┼───────┼──────┼────────┼──────┼──────────┤  │
│  │Mario S. │  5    │  3   │  1     │20.0% │  3.2h    │  │
│  └─────────┴───────┴──────┴────────┴──────┴──────────┘  │
├─────────────────────────────────────────────────────────┤
│  Provas Atrasadas (2)                                   │
│  ┌──────────┬─────────┬──────────┬───────┬────────────┐ │
│  │Nome      │Req      │Vendedor  │Status │Dias Atraso │ │
│  ├──────────┼─────────┼──────────┼───────┼────────────┤ │
│  │Arte XYZ  │REQ-001  │Mario S.  │Retir. │  3.5 dias  │ │
│  └──────────┴─────────┴──────────┴───────┴────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Componentes

| Componente | Responsabilidade |
|------------|-----------------|
| `RelatoriosPage` | Pagina principal. Fetch + filtro periodo + layout |
| Cards de resumo (inline) | 4 cards: total geral, tempo medio, taxa reprovacao geral, distribuicao por rota |
| Tabela por vendedor (inline) | Tabela com metricas por vendedor (reuso do padrao CSS de `/usuarios` e `/provas`) |
| Tabela de atrasadas (inline) | Lista de provas atrasadas com dias de atraso |
| Filtro de periodo (inline) | Inputs date + botao aplicar (reuso do padrao de C07) |
| Botao CSV (inline) | Trigger download do endpoint CSV |

### Estados e Fluxo

1. **Carga inicial:** `GET /api/v1/provas/relatorios` com periodo default (ultimos 30 dias).
2. **Filtro de periodo:** Usuario altera datas → novo fetch com params atualizados.
3. **Export CSV:** Click em botao "Exportar CSV" → `fetch` direto (nao `apiFetch`, pois retorna binario) com `response.blob()` → `URL.createObjectURL` → download automatico. Mesmo padrao usado para `/etiqueta.pdf` e `/qr-code.png` (CLAUDE.md: "Binarios no frontend").
4. **Sem Realtime:** Relatorios sao consultados esporadicamente. Sem subscription Supabase Realtime. Refresh manual via botao ou re-aplicacao do filtro.

### Hooks novos

| Hook | Responsabilidade |
|------|-----------------|
| `useRelatorios(getToken)` | GET `/provas/relatorios` + params periodo + retorno tipado |
| `useExportCsv(getToken)` | GET `/provas/relatorios/csv` + trigger download blob |

### Graficos Recharts (3 visualizacoes)

Mario solicitou 3 graficos via Recharts na pagina de relatorios:

| Grafico | Tipo | Dados | Descricao |
|---------|------|-------|-----------|
| Total de Provas Ativas | `PieChart` (donut) | Distribuicao por status (excluindo CANCELADA e RECEBIDA) | Visualiza quantas provas estao em cada estagio ativo do fluxo |
| Tempo Medio de Aprovacao | `BarChart` (horizontal) | `por_vendedor[].tempo_medio_aprovacao_horas` | Compara velocidade de aprovacao entre vendedores |
| Vendedor com Mais Artes | `BarChart` (horizontal) | `por_vendedor[].total_provas` ordenado DESC | Ranking de volume por vendedor |

Os graficos ficam entre os cards de resumo e as tabelas, em grid 3 colunas (desktop)
ou empilhados (mobile). Usam os tokens de cor do `globals.css`.

### Dependencias novas

| Pacote | Versao | Justificativa |
|--------|--------|---------------|
| `recharts` | `^2.15` | Graficos de relatorios (DAT v2.0 especifica Recharts). Import seletivo para tree-shaking. |

**Nota:** Recharts foi adicionado e removido na Wave 4 (ADR-093) por nao estar no Figma
do dashboard. Na Wave 5, o stakeholder solicitou explicitamente graficos para relatorios.

### Ativacao do menu

`layout.tsx`: alterar o item "Relatorios" de placeholder (sem href) para `href: "/relatorios"`.

### Tipos TypeScript novos

```typescript
// frontend/src/lib/types/relatorio.ts

interface VendedorRelatorio {
  vendedor_id: string;
  vendedor_nome: string;
  vendedor_localizacao: string | null;
  total_provas: number;
  aprovadas: number;
  reprovadas: number;
  taxa_reprovacao_pct: number;
  tempo_medio_aprovacao_horas: number | null;
}

interface ProvaAtrasada {
  prova_id: string;
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_nome: string;
  status: string;
  rota: string | null;
  dias_atraso: number;
  ultima_movimentacao_em: string;
}

interface DistribuicaoRota {
  PADRAO: number;
  DIRETA: number;
  SEM_ROTA: number;
}

interface RelatorioResponse {
  periodo: { inicio: string; fim: string };
  total_geral: number;
  tempo_medio_aprovacao_horas: number | null;
  total_atrasadas: number;
  distribuicao_por_rota: DistribuicaoRota;
  por_vendedor: VendedorRelatorio[];
  atrasadas: ProvaAtrasada[];
  atualizado_em: string;
}
```

---

## 6. Storage R2

**Nenhuma alteracao necessaria.** Relatorios nao interagem com artes de provas.
O bucket `rastreio-provas-artes` permanece inalterado.

---

## 7. Plano de Testes

### Camada 1 — Unitarios (backend)

| Teste | Cobertura |
|-------|-----------|
| `test_relatorio_schemas_validation` | PeriodoFiltro rejeita inicio > fim |
| `test_relatorio_schemas_defaults` | PeriodoFiltro aceita datas validas |
| `test_relatorio_vendedor_taxa_reprovacao` | Calculo correto: (reprovadas/total)*100 |
| `test_relatorio_vendedor_taxa_zero_division` | total_provas=0 → taxa=0.0 |
| `test_relatorio_tempo_medio_null` | Sem aprovacoes → tempo_medio=None |
| `test_relatorio_distribuicao_rota_null` | Provas sem rota contam como SEM_ROTA |
| `test_relatorio_atrasadas_exclui_terminais` | RECEBIDA/CANCELADA nunca aparecem como atrasadas |
| `test_relatorio_atrasadas_dias_calculo` | Dias de atraso calculados corretamente |

**Meta:** >= 80% das linhas do handler de relatorios.

### Camada 2 — Integracao (backend)

| Teste | Cobertura |
|-------|-----------|
| `test_relatorios_endpoint_200_admin` | Admin recebe 200 com estrutura correta |
| `test_relatorios_endpoint_403_vendedor` | Vendedor recebe 403 |
| `test_relatorios_endpoint_401_sem_auth` | Sem auth recebe 401 |
| `test_relatorios_endpoint_422_periodo_invalido` | inicio > fim retorna 422 |
| `test_relatorios_filtro_periodo_filtra_provas` | Provas fora do periodo nao aparecem no total |
| `test_relatorios_por_vendedor_consistente` | Soma dos totais por vendedor = total_geral |
| `test_relatorios_atrasadas_lista_com_dias` | Lista retorna provas com dias_atraso > 0 |
| `test_relatorios_csv_200_admin` | Admin recebe 200 com Content-Type text/csv |
| `test_relatorios_csv_403_vendedor` | Vendedor recebe 403 |
| `test_relatorios_csv_conteudo_correto` | CSV tem header + linhas correspondentes |
| `test_relatorios_csv_filtro_periodo` | CSV respeita filtro de periodo |
| `test_relatorios_csv_encoding_utf8` | CSV com acentos renderiza corretamente |

**Meta:** 100% dos 2 endpoints cobertos.

### Camada 3 — Frontend

| Teste | Metodo |
|-------|--------|
| Pagina renderiza com dados do backend | Smoke manual |
| Filtro de periodo filtra corretamente | Smoke manual |
| Tabela por vendedor exibe metricas corretas | Smoke manual |
| Lista de atrasadas exibe dias de atraso | Smoke manual |
| Botao CSV dispara download | Smoke manual |
| CSV abre corretamente no Excel | Smoke manual |
| Responsividade mobile (>= 5") | Smoke manual |
| `tsc --noEmit` limpo | CI |
| `next lint` limpo | CI |
| `next build` OK | CI |

---

## 8. Riscos e Pontos de Atencao

### R-01 — Volume baixo pode mascarar problemas de performance

**Risco:** Com 13 provas, qualquer query roda em <10ms. Se o volume crescer para 10k+,
a query de tempo medio (JOIN em movimentacoes) e a lista de atrasadas podem degradar.

**Mitigacao:** Os indexes existentes cobrem os cenarios:
- `idx_movimentacoes_prova_data (prova_id, created_at DESC)` para tempo medio
- `idx_provas_vendedor` para GROUP BY vendedor
- `idx_provas_status_created` para filtro por periodo + status

Para volume >10k, considerar materialized view em wave futura.

### R-02 — Horas corridas vs horas uteis no tempo medio

**Risco:** O tempo medio de aprovacao usa horas corridas (consistente com ADR-091 Wave 4).
Provas criadas sexta 17h e aprovadas segunda 9h mostrarao 64h, nao 10h uteis.

**Mitigacao:** Aceito na Wave 4 (decisao Mario). Manter consistencia. Se necessario,
Wave 6 pode evoluir para calculo real de horas uteis.

### R-03 — Taxa de reprovacao com multiplos ciclos

**Risco:** Uma prova pode ser reprovada no ciclo 1, reiniciada e aprovada no ciclo 2.
A query conta a prova como "aprovada" E "reprovada" simultaneamente.

**Mitigacao:** A taxa reflete a realidade operacional: a prova FOI reprovada e depois
aprovada. O denominador e `total_provas` (nao total_eventos). Documentar no tooltip da UI.

### R-04 — CSV sem limite de linhas

**Risco:** O endpoint CSV retorna todas as provas do periodo sem paginacao. Com volume
alto (>10k linhas), o response pode ser grande.

**Mitigacao:** `StreamingResponse` do FastAPI envia chunks, nao carrega tudo em memoria.
Para o volume projetado (< 500 provas), o CSV sera < 50 KB. Limite explicito de 10.000
linhas com mensagem de erro se excedido (safety valve).

### R-05 — Sem Figma para relatorios

**Risco:** Nao ha design Figma para a pagina de relatorios. O layout proposto (secao 5)
e baseado nos padroes visuais das Waves 2-4.

**Mitigacao:** Layout segue tokens e padroes existentes. Se o stakeholder desejar ajustes
visuais, podem ser aplicados apos a implementacao inicial sem impacto no backend.

### R-06 — Supabase free tier: limites de query

**Risco:** O free tier do Supabase nao tem limites de queries por hora, mas tem limite de
500 MB de storage e 50k requests de Auth por mes. Relatorios admin-only com acesso
esporadico nao impactam esses limites.

**Mitigacao:** Monitorar via Supabase Dashboard. Volume projetado: <100 acessos/dia a relatorios.

---

## 9. Ordem de Implementacao em Blocos

### Bloco 5.1 — Backend: Endpoint de Relatorios JSON

**Escopo:**
1. Criar Pydantic schemas: `PeriodoFiltro`, `VendedorRelatorio`, `ProvaAtrasada`, `DistribuicaoRota`, `RelatorioResponse`
2. Implementar `GET /api/v1/provas/relatorios` com:
   - 6 indicadores RF-015 (total_geral, tempo_medio, atrasadas, distribuicao_rota, por_vendedor, taxa_reprovacao)
   - Filtro de periodo (inicio/fim com defaults)
   - RBAC admin-only via `get_admin_user`
   - Reuso de `_scoping_filter` e padrao de calculo de atrasadas (Wave 4)
3. Testes unitarios + integracao (meta: >= 12 testes)
4. Ruff + pytest com cobertura

**Entregaveis:** Endpoint funcional, testes passando, schemas documentados.

**Arquivos novos:**
- `backend/app/domain/schemas/relatorio.py`

**Arquivos modificados:**
- `backend/app/api/v1/provas.py` — +2 handlers (relatorios JSON + CSV)
- `backend/tests/test_provas_api.py` — +testes relatorios

### Bloco 5.2 — Backend: Exportacao CSV

**Escopo:**
1. Implementar `GET /api/v1/provas/relatorios/csv`
   - StreamingResponse com csv.writer
   - Mesmos filtros de periodo do endpoint JSON
   - RBAC admin-only
   - Header UTF-8 BOM para compatibilidade Excel
2. Testes de integracao (Content-Type, conteudo, encoding, RBAC)
3. Ruff + pytest

**Entregaveis:** Download CSV funcional, testes passando.

**Arquivos modificados:**
- `backend/app/api/v1/provas.py` — +handler CSV (mesmo router)
- `backend/tests/test_provas_api.py` — +testes CSV

### Bloco 5.3 — Frontend: Pagina de Relatorios

**Escopo:**
1. Criar rota `/relatorios` (page.tsx + CSS Module)
2. Hook `useRelatorios` para fetch do endpoint JSON
3. Hook `useExportCsv` para download do CSV
4. Layout com 4 cards de resumo + 2 tabelas (vendedores + atrasadas)
5. Filtro de periodo com inputs date + botao aplicar
6. Botao "Exportar CSV" com download via blob
7. Tipos TypeScript (`relatorio.ts`)
8. Ativar item do menu ("Relatorios" → href="/relatorios")
9. `tsc --noEmit` + `next lint` + `next build`

**Entregaveis:** Pagina funcional com dados do backend, CSV baixando.

**Arquivos novos:**
- `frontend/src/app/(dashboard)/relatorios/page.tsx`
- `frontend/src/app/(dashboard)/relatorios/relatorios.module.css`
- `frontend/src/hooks/useRelatorios.ts`
- `frontend/src/hooks/useExportCsv.ts`
- `frontend/src/lib/types/relatorio.ts`

**Arquivos modificados:**
- `frontend/src/app/(dashboard)/layout.tsx` — 1 palavra (href)

### Bloco 5.4 — Closeout + Documentacao

**Escopo:**
1. Atualizar `CHANGELOG.md` com entrada da Wave 5
2. Atualizar `DECISIONS.md` com novos ADRs
3. Atualizar `CLAUDE.md` (tabela de waves, endpoints, rotas frontend)
4. Verificacao de advisors Supabase pos-implementacao
5. Metricas finais consolidadas

**Entregaveis:** Documentacao completa, advisors limpos.

---

## Resumo de Impacto

| Categoria | Antes (Wave 4) | Depois (Wave 5) | Delta |
|-----------|----------------|-----------------|-------|
| Testes backend | 424 | ~444+ | +20+ |
| Rotas backend | 29 | 31 | +2 |
| Rotas frontend | 9 | 10 | +1 |
| Policies RLS | 12 | 12 | 0 |
| alembic_version | 009 | 009 | 0 |
| Deps npm prod | 8 | 9 | +1 (recharts) |
| Tabelas dominio | 6 | 6 | 0 |
| Migrations Alembic | 9 | 9 | 0 |
| RLS SQL files | 7 | 7 | 0 |
