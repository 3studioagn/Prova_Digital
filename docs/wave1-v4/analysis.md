# Wave 1 (v4.0) — Componente 05 (Atualização v4.0) · Análise Read-Only (Gate 1)

**Data:** 2026-04-30
**Branch alvo do Gate 1:** `wave1-v4/analysis`
**Branch alvo do Gate 2:** `wave1-v4/componente-05` (não criada ainda)
**Autor:** agente de execução
**Status:** Aguardando autorização para Gate 2.

> **AVISO DE NOMENCLATURA — leia antes de qualquer coisa.**
>
> O Documento de Requisitos v4.0 (Seção 6) usa os perfis humanos
> **3Studio · Vendedor · Motorista · Clicheria**. O enum PostgreSQL hoje em
> produção (`setor_enum`) usa valores em CAIXA ALTA: `STUDIO · VENDEDOR ·
> MOTORISTA · CLICHERIA`. O perfil "3Studio" da Matriz **não é** simplesmente
> `setor=STUDIO`: é `is_admin = true`. O modelo de dados da v3.0 separa
> `setor` (categoria operacional) de `is_admin` (booleano de privilégio).
> Esta análise mantém esse modelo intacto — Wave 1 v4.0 **não cria nem
> remove perfis** (item explícito do escopo do prompt).
>
> Mapeamento canônico desta wave:
>
> | Perfil da Matriz | Predicado em SQL/TS                  |
> |------------------|--------------------------------------|
> | 3Studio          | `is_admin = true`                    |
> | Vendedor         | `is_admin = false AND setor = VENDEDOR` |
> | Motorista        | `is_admin = false AND setor = MOTORISTA` |
> | Clicheria        | `is_admin = false AND setor = CLICHERIA` |
>
> Hoje em produção todo `setor=STUDIO` tem `is_admin=true` (4 usuários
> ativos: 2 STUDIO admin + 2 VENDEDOR FILIAL). O modelo permite STUDIO sem
> admin, mas a Matriz da v4.0 **não exige** que o tratemos diferente — basta
> garantir que tal usuário cai no comportamento default (sem acesso elevado).

---

## Sumário

- [0. Confirmação de leitura](#0-confirmação-de-leitura)
- [1. Validação MCP](#1-validação-mcp)
- [2. Inventário do RBAC atual (estado v3.0)](#2-inventário-do-rbac-atual-estado-v30)
- [3. Mapeamento da Matriz de Acesso para a infraestrutura](#3-mapeamento-da-matriz-de-acesso-para-a-infraestrutura)
- [4. Desenho de `access-matrix.ts`](#4-desenho-de-access-matrixts)
- [5. Desenho do middleware](#5-desenho-do-middleware)
- [6. Desenho das políticas RLS](#6-desenho-das-políticas-rls)
- [7. Desenho do hook `useAuthorization`](#7-desenho-do-hook-useauthorization)
- [8. Plano de migração das chamadas existentes](#8-plano-de-migração-das-chamadas-existentes-refactor-coordenado)
- [9. Estratégia de testes](#9-estratégia-de-testes)
- [10. Migrations previstas](#10-migrations-previstas)
- [11. Riscos e pontos de atenção](#11-riscos-e-pontos-de-atenção)

---

## 0. Confirmação de leitura

### 0.1 Arquivos de contexto vivo do repositório (estado atual)

| # | Arquivo | Status | Observação |
|---|---|---|---|
| 1 | `CLAUDE.md` | Lido (contexto inicial) | 7 waves v3.0 entregues, 4 usuários ativos, 2 tabelas em `supabase_realtime` (`provas_digitais`). |
| 2 | `DECISIONS.md` | 4029 linhas; consultado por busca dirigida (ADR-014/018/024–029/082). Não lido linearmente — arquivo excede 256 KB do tool. | Sem inconsistências detectadas com o estado de partida descrito no Gate 1. |
| 3 | `CHANGELOG.md` | 7959 linhas; consultado por busca dirigida (Wave 1 + Wave 6). | Wave 6 closeout 2026-04-29; commit "Versão 1 do sistema entregue" 2026-04-30 = início real da v4.0. |
| 4 | `docs/db/schema.sql` | Lido linha-a-linha (298 linhas). | Snapshot atualizado em 2026-04-27. RLS 007 aplicada (`provas_digitais` em `supabase_realtime`). |
| 4a | `backend/migrations/rls/*.sql` | 7 arquivos enumerados via Glob; conteúdo cruzado com `pg_policies` (ver Seção 1). | Nenhuma policy "fantasma" — banco e arquivos batem. |
| 4b | `backend/migrations/versions/*.py` | 11 migrations enumeradas; `alembic_version` confirmado em 011. | OK. |

### 0.2 Documentos de produto da v4.0 (estado de destino)

| # | Documento | Caminho real | Status |
|---|---|---|---|
| 5 | Requisitos v4.0 | `C:\Users\mario.souza\Desktop\Rastreio Prova Digital\RequisitosProvasDigitais_v4_0.docx` | Extraído para `docs/wave1-v4/_extracted/requisitos_v4.md` (43 KB) e lido integralmente. |
| 6 | Backlog v4.0 | `C:\Users\mario.souza\Desktop\Rastreio Prova Digital\BACKLOG_RastreioProvasDigitais_v4_0.docx` | Extraído para `docs/wave1-v4/_extracted/backlog_v4.md` (35 KB) e lido integralmente. |
| 7 | DAT v3.0 | `C:\Users\mario.souza\Desktop\Rastreio Prova Digital\DAT_RastreioProvasDigitais_v3_0.docx` | Extraído para `docs/wave1-v4/_extracted/dat_v3.md` (23 KB) e lido integralmente. |
| 8 | UML v4.0 | `C:\Users\mario.souza\Desktop\Rastreio Prova Digital\UML_RastreioProvasDigitais_v4_0.drawio` | **Localizado, não lido.** É XML do drawio com geometria de diagrama. Para Wave 1 v4.0 (RBAC) o conteúdo de classes/estados não é crítico — toda a especificação canônica do RBAC está nas Seções 5 e 6 do Requisitos v4.0 (estados + Matriz). Será relevante para Waves 2/3 v4.0 (estado-machine + rota). **Reportar ao solicitante** se quiser que o UML seja lido também antes do Gate 2. |

> **Divergência de path declarada no prompt vs. realidade:** o prompt
> indicou `Downloads/` para os 4 documentos, mas eles estão em
> `Desktop/Rastreio Prova Digital/`. Confirmado por `ls`. Sem mudança de
> conteúdo — apenas de localização.

### 0.3 Código-fonte do projeto (apenas leitura nesta fase)

| # | Foco | Resultado |
|---|---|---|
| 9 | Componente 03 (Login + sessão) | `frontend/src/middleware.ts` + `frontend/src/lib/supabase/middleware.ts` lidos. Backend `app/api/deps.py` lido. JWT do Supabase Auth verificado via `auth.users` MCP — claims customizados **ausentes** (`raw_app_meta_data` apenas `{provider, providers}`; `raw_user_meta_data` apenas `{email_verified}`). **Conclusão crítica:** `setor` e `is_admin` **não estão no JWT** — o backend lê da tabela `usuarios` via `auth_uid`. |
| 10 | Componente 04 (Cadastro de usuários) | Inventário backend e frontend feito por agentes (Seção 2 abaixo). Modelo `Usuario` em `backend/app/db/models.py` confirma colunas `auth_uid`, `setor`, `localizacao`, `is_admin`, `ativo`. |
| 11 | Inventário completo de checagens RBAC | Realizado via 2 agentes Explore em paralelo. Resultado consolidado na Seção 2. |

---

## 1. Validação MCP

### 1.1 Supabase

- **Projeto ativo:** `rwxlpwmnkekzuurgthkr` (Rastreio Provas Digitais), região `sa-east-1`, status `ACTIVE_HEALTHY`, Postgres 17.6.1.104.
- **Tabelas de domínio confirmadas (schema `public`):** `usuarios`, `provas_digitais`, `movimentacoes`, `etiquetas`, `audit_logs`, `configuracoes_sistema` + `alembic_version`. Todas com `relrowsecurity = true`. **`relforcerowsecurity = false` em todas** — o `service_role` do backend continua bypassando RLS por design (ADR-046/049).
- **Policies em `pg_policies` (12 ao total — bate com schema.sql):**

  | Tabela | Comando | Policy | Predicado-resumo |
  |---|---|---|---|
  | `audit_logs` | SELECT | `pol_audit_select` | `is_admin=true` |
  | `configuracoes_sistema` | SELECT | `pol_config_select` | `is_admin=true` |
  | `configuracoes_sistema` | UPDATE | `pol_config_update` | `is_admin=true` |
  | `etiquetas` | SELECT | `pol_etiquetas_select` | `is_admin=true` OR `prova_id IN (provas do vendedor)` |
  | `movimentacoes` | INSERT | `pol_movimentacoes_insert` | `is_admin=true` (CHECK) |
  | `movimentacoes` | SELECT | `pol_movimentacoes_select` | `is_admin=true` OR `prova_id IN (provas do vendedor)` OR `usuario_id = self` OR `setor=MOTORISTA AND prova.status=COM_MOTORISTA` OR `setor=CLICHERIA AND prova.status IN (clicheria-states)` |
  | `provas_digitais` | INSERT | `pol_provas_insert` | `is_admin=true` (CHECK) |
  | `provas_digitais` | SELECT | `pol_provas_select` | `is_admin=true` OR `vendedor_id=self` OR `setor=MOTORISTA AND status=COM_MOTORISTA` OR `setor=CLICHERIA AND status IN (clicheria-states)` |
  | `provas_digitais` | UPDATE | `pol_provas_update` | `is_admin=true` |
  | `usuarios` | INSERT | `pol_usuarios_insert` | `is_admin=true` (CHECK) |
  | `usuarios` | SELECT | `pol_usuarios_select` | self OR `is_admin=true` |
  | `usuarios` | UPDATE | `pol_usuarios_update` | `is_admin=true` |

  **Padrão de referência detectado:** todas as policies usam
  `EXISTS (SELECT 1 FROM usuarios u WHERE u.auth_uid = (SELECT auth.uid()) AND ...)`
  — **não** `auth.jwt() ->> 'setor'` (como propõe o DAT v3.0 Seção 7.2).
  Ver Seção 6.0 desta análise para a discussão dessa divergência e a
  decisão proposta.

- **Setores em uso (DISTINCT em `usuarios`):** `STUDIO`, `VENDEDOR`. Os outros dois (`MOTORISTA`, `CLICHERIA`) existem no enum mas **não há usuário cadastrado**. Isso é compatível com o estado de produção atual e não bloqueia a wave — a Matriz precisa cobrir os 4 perfis mesmo que 2 estejam vazios.
- **Distribuição:** 2× `STUDIO/–/admin=true` + 2× `VENDEDOR/FILIAL/admin=false` = 4 usuários ativos. Nota: o CLAUDE.md fala em "3 usuários" — drift menor, não bloqueia.
- **Claims do JWT (CRÍTICO):** validado via `auth.users JOIN public.usuarios`. `raw_app_meta_data` para todos os 4 usuários: `{"provider": "email", "providers": ["email"]}`. `raw_user_meta_data`: `{"email_verified": true}`. **Não há claim `setor`, `user_id`, `is_admin`, ou similar.** Hoje, o `auth.uid()` retorna o `id` da tabela `auth.users`, e o backend (e RLS) faz lookup em `public.usuarios.auth_uid` para obter `setor`/`is_admin`.
- **Advisor (security):**
  - `INFO rls_enabled_no_policy` em `public.alembic_version` — **intencional** (ADR-025, mantido na Wave 0/1).
  - `WARN auth_leaked_password_protection` — **WONTFIX** (plano pago, ADR-027).
  - **Nenhum advisor crítico atribuível à Wave 1 v4.0.**
- **Advisor (performance):** 13× `INFO unused_index` (vários idx_* em `usuarios`, `provas_digitais`, `movimentacoes`, `audit_logs`, `configuracoes_sistema`). **Falsos positivos pós-deploy** — banco tem ~17 audit_logs, 5 movimentacoes, 2 provas. Após uso real os índices passam a aparecer. Não bloqueia esta wave.

### 1.2 Cloudflare

- **Account:** `20ab724c91f6bda669eecfe7c51c9171` (3studioagn@gmail.com), criada 2026-04-06. **Saudável.**
- **Não há trabalho novo** de R2/Workers/KV nesta wave. Sem alterações.

### 1.3 Veredito MCP

✅ **Pré-requisitos OK** — banco saudável, 4 usuários cobrindo 2 dos 4 setores, 12 policies RLS aplicadas, advisors limpos para esta wave.

⚠️ **Bloqueio potencial superado por adaptação de design:** o DAT v3.0
Seção 7.2 propõe SQL de RLS lendo `auth.jwt() ->> 'setor'`. O JWT atual
**não tem** esse claim. Resposta proposta na Seção 6.0: **manter o padrão
existente** (subquery EXISTS contra `usuarios`) e documentar a divergência
do DAT no `DECISIONS.md`. Isso evita tocar configuração do Supabase Auth
(Custom Access Token Hook), o que está fora do escopo do prompt
("**Proibido** tocar configurações de deploy, variáveis de ambiente ou
segredos sem autorização").

---

## 2. Inventário do RBAC atual (estado v3.0)

> Os inventários completos foram produzidos por dois agentes Explore em
> paralelo (backend FastAPI e frontend Next.js). Os resumos abaixo são as
> camadas que esta análise consolida; o material exaustivo está
> imediatamente disponível em mensagens prévias do Gate 1 (não
> reproduzimos byte-a-byte aqui para manter o `analysis.md` legível).

### 2.1 Camadas RBAC já existentes

| Camada | Mecanismo | Granularidade | Fonte de verdade |
|---|---|---|---|
| **Backend — Dependencies** | `Depends(get_admin_user)` em endpoints administrativos | Por endpoint | `usuarios.is_admin` |
| **Backend — Scoping** | `_scoping_filter(user)` aplicado em SELECTs | Por linha (vendedor própria; motorista/clicheria por status) | `usuarios.setor` + `provas_digitais.vendedor_id`/`status` |
| **Backend — State Machine** | `validar_transicao()` em `state_machine.py` | Por par (transição × setor) | Tabela `_TRANSICOES_VALIDAS` em `state_machine.py` |
| **DB — RLS** | 12 policies em `public.*` | Por linha (espelha o scoping do backend) | Subquery `EXISTS` contra `usuarios` |
| **DB — Triggers de imutabilidade** | `fn_bloquear_alteracao()` em `movimentacoes`, `etiquetas`, `audit_logs` | Por operação | RNF-005 |
| **DB — REVOKE GRANT-level** | `audit_logs` sem INSERT/UPDATE/DELETE para `anon`/`authenticated` (RLS 008 — Wave 6) | GRANT | RNF-005 (3ª camada de defesa) |
| **Frontend — Layout `MAIN_NAV`/`SECONDARY_NAV`** | Filtra itens com `adminOnly:true` | Por item de menu | `useCurrentUser().is_admin` |
| **Frontend — Componente `AdminActions`** | Retorna `null` se `!user.is_admin` | Por componente | `useCurrentUser` |
| **Frontend — `useGlobalShortcuts.visibleShortcuts`** | Filtra atalhos `g r`/`g a` por `adminOnly` | Por atalho | `isAdmin` recebido como prop |
| **Frontend — `/auditoria` page guard** | `if (!me.is_admin) return <Restricted />` proativo | Por página | `useCurrentUser` |
| **Frontend — `/relatorios` reactive guard** | Tenta fetch, recebe 403, exibe "Acesso restrito" | Por página | Backend |
| **Frontend — Filtro de vendedor em `/provas`** | `<select disabled>` se `!is_admin` | Por controle | `useCurrentUser` |
| **Frontend — Middleware** | Apenas autenticação. Sem checagem de perfil. | Global | Sessão Supabase |

### 2.2 Lista compacta de checagens ad-hoc — alvos do refactor

> Numeração (B = backend, F = frontend) usada como chave nas Seções 8 e 9.
> Linhas aproximadas (∗) — confirmar no Gate 2.

#### Backend

| ID | Arquivo | Linha (∗) | Checagem | Ação proposta |
|----|---|---|---|---|
| B1 | `app/api/deps.py` | 95–104 | `get_admin_user` (verifica `user.is_admin`) | **Manter** como helper legacy. O guard primário passa a ser `enforce_access_for("rota_chave", user)` (Seção 4). `get_admin_user` continuará disponível para endpoints "puros admin" simples. |
| B2 | `app/api/deps.py` | 107–120 | `require_role(*allowed_setors)` | **Remover** (factory nunca usado). Ver Seção 8. |
| B3 | `app/api/v1/users.py` | 192–193 | `if not is_admin and current_user.id != user.id: 403` | **Substituir** por `enforce_access_for("usuarios.detail", user, target_user_id=user.id)` ou manter como invariante "self ou admin" (esta NÃO é uma célula da Matriz — ainda assim estabilizar via helper). |
| B4 | `app/api/v1/provas.py` | 660–676 | `_scoping_filter(user)` | **Manter** mas mover para `app/access/scopes.py` e referenciar pelo nome da rota (`provas.list`). RLS espelha. |
| B5 | `app/api/v1/provas.py` | múltiplas | `Depends(get_admin_user)` em POST `/`, POST `/upload-url`, POST `/cancelar`, POST `/reiniciar-ciclo` | **Substituir** por `enforce_access_for("provas.create" / "provas.cancel" / "provas.restart", user)`. |
| B6 | `app/api/v1/provas.py` | scan/transicoes | Validação de transição em `state_machine.validar_transicao()` | **Manter intacto** — não é decisão de página, é decisão de transição (RN-002/004). Wave 3 v4.0 reformula. |
| B7 | `app/api/v1/configuracoes.py` | 48, 91, 150 | `Depends(get_admin_user)` | **Substituir** por `enforce_access_for("configuracoes.*", user)`. |
| B8 | `app/api/v1/audit_log.py` | 126, 228, 290 | `Depends(get_admin_user)` | **Substituir** por `enforce_access_for("auditoria.*", user)`. |
| B9 | `app/api/v1/reports.py` | 1073, 1159 | `Depends(get_admin_user)` | **Substituir** por `enforce_access_for("relatorios.*", user)`. |
| B10 | `app/services/state_machine.py` | 209–228 | Cancelamento exige `setor=STUDIO OR is_admin` | **Manter intacto** — é regra de negócio (RN-005), não Matriz de Acesso. |
| B11 | `app/api/v1/provas.py` | 252–280 | Validação de vendedor em criação (setor + ativo + localização) | **Manter intacto** — invariante de domínio, não RBAC de página. |
| B12 | `app/api/v1/users.py` | 221–244 | Invariantes RN-010 (admin não pode remover próprio is_admin; sistema mantém ≥1 admin) | **Manter intacto** — regras de negócio. |

#### Frontend

| ID | Arquivo | Linha (∗) | Checagem | Ação proposta |
|----|---|---|---|---|
| F1 | `src/middleware.ts` + `lib/supabase/middleware.ts` | 4–47 | Apenas auth; `/login → /usuarios` para autenticado | **Substituir** por middleware de RBAC + redirect "página inicial do perfil". Ver Seção 5. |
| F2 | `src/app/(dashboard)/layout.tsx` MAIN_NAV/SECONDARY_NAV | 48–68, 245–268 | Filtragem por `adminOnly` | **Substituir** filtragem hardcoded por `ACCESS_MATRIX` (cada item de nav lê `useAuthorization(href).hasAccess`). |
| F3 | `src/hooks/useGlobalShortcuts.ts` | 38–94 | `SHORTCUT_DEFS` com `adminOnly:true` em `g r` e `g a` | **Substituir** filtragem hardcoded por consulta a `ACCESS_MATRIX` por path. |
| F4 | `src/components/KeyboardShortcutsHelp.tsx` | recebe array filtrado | Sem mudança | **Manter intacto** (já recebe filtrado). |
| F5 | `src/app/(dashboard)/provas/[id]/AdminActions.tsx` | 34–102 | `if (!user.is_admin) return null` | **Substituir** por `useAuthorization("provas.cancel").hasAccess` + `useAuthorization("provas.restart").hasAccess`. |
| F6 | `src/app/(dashboard)/auditoria/page.tsx` | 373–386 | Guard proativo `if (!me.is_admin) <Restricted />` | **Substituir** por `useAuthorization("auditoria")` + componente `<Restricted />` reutilizável. |
| F7 | `src/app/(dashboard)/relatorios/page.tsx` | 129–146 | Guard reativo (parsing de mensagem de erro) | **Substituir** por guard proativo via `useAuthorization("relatorios")`. **Promove de "reativo" para "proativo".** |
| F8 | `src/app/(dashboard)/usuarios/page.tsx` | 236–245 | Botão "Novo usuário" sem guard | **Adicionar** guard de página + ocultar botão se `!useAuthorization("usuarios").hasAccess`. |
| F9 | `src/app/(dashboard)/configuracoes/page.tsx` | — | Sem guard explícito | **Adicionar** guard de página via `useAuthorization("configuracoes")`. |
| F10 | `src/app/(dashboard)/nova-prova/page.tsx` | — | Sem guard explícito | **Adicionar** guard de página via `useAuthorization("provas.create")`. |
| F11 | `src/app/(dashboard)/provas/page.tsx` | 102–326 | Filtro vendedor `disabled` se `!is_admin` | **Substituir** por `useAuthorization("provas.list").scope` — quando scope = "self" o filtro fica disabled (ou oculto). |
| F12 | `src/app/(dashboard)/escanear/page.tsx` | — | Sem guard de página (transições vêm do backend) | **Manter intacto** — escanear é universal na Matriz; a verificação por transição continua sendo state-machine. |
| F13 | `src/hooks/useCurrentUser.ts` | 7–54 | Hook que busca `/users/me` | **Manter intacto**, mas estender o tipo `UserInfo` para `setor: SetorType` (string union, não `string` solto). |

### 2.3 Lacunas identificadas

| ID | Origem | Descrição | Severidade |
|----|---|---|---|
| L-RLS-1 | Comparação Matriz × policies atuais | `etiquetas.SELECT` hoje só admin + vendedor. **Matriz exige Motorista (escopo "Em Trânsito") e Clicheria (escopo "Clicheria-states") visualizem prova de detalhe** — embutindo etiqueta no PDF endpoint via service_role isso funciona, mas para defesa em profundidade RLS precisa cobrir esses dois perfis. | Média (closeable) |
| L-RLS-2 | Comparação Matriz × policies atuais | `provas_digitais.SELECT` hoje cobre admin + vendedor + motorista (status COM_MOTORISTA) + clicheria (3 status). **Faltam dois detalhes:** o motorista da Matriz v4.0 lista provas "Em Trânsito" — coincide com `COM_MOTORISTA` legado; o clicheria já está OK. **Acordo desta wave:** manter o nome legado COM_MOTORISTA (Wave 3 v4.0 reformula para 3 contextos). | Baixa |
| L-RLS-3 | Comparação Matriz × policies atuais | `usuarios.SELECT` hoje cobre self + admin. Matriz não exige outros perfis lerem `usuarios` — **OK**. | — |
| L-RLS-4 | Comparação Matriz × policies atuais | `audit_logs`/`configuracoes_sistema` cobertos com is_admin. **OK**. | — |
| L-MIDDLE-1 | Inventário frontend | Middleware atual redireciona authenticated `/login` → `/usuarios`. **Vendedor/Motorista/Clicheria não têm acesso a `/usuarios`** (○ na Matriz). Bug de UX existente. | **Alta — corrigir nesta wave (página inicial por perfil).** |
| L-FE-1 | Inventário frontend | `/relatorios` é guard reativo (espera 403, parseia mensagem). | Média (UX) |
| L-FE-2 | Inventário frontend | `/usuarios` botão "Novo usuário" visível para qualquer autenticado. | Média (UX) |
| L-FE-3 | Inventário frontend | `useGlobalShortcuts` lista shortcuts hardcoded; precisa virar consulta à Matriz. | Baixa |

### 2.4 Excessos (defesa em profundidade — manter)

| ID | Onde | Por quê manter |
|----|---|---|
| E1 | Triple-defense de `audit_logs` (trigger imutabilidade + RLS deny + REVOKE GRANT) | RNF-005 — 3 camadas independentes. Não tocar. |
| E2 | Backend scoping + RLS scoping (espelhados) | A camada superior bloqueia a página; a inferior bloqueia o dado. **A Wave 1 v4.0 codifica formalmente essa equivalência via testes.** |
| E3 | State machine valida transição (setor) + endpoint admin valida ação administrativa | Separação correta: transição = regra de domínio; ação administrativa = RBAC de página. |

---

## 3. Mapeamento da Matriz de Acesso para a infraestrutura

A Matriz da Seção 6 do `RequisitosProvasDigitais_v4_0.docx` tem **13 linhas**.
Mapeamento para as rotas/recursos reais do projeto (Wave 1 v4.0 não altera
o conjunto de rotas — apenas a aplicação do acesso):

> Convenção: `●` = full · `◐` = parcial · `○` = sem acesso. As colunas "RLS
> tabela impactada" identificam onde a defesa inferior é aplicada;
> "Camada UI" identifica que tipo de gating o frontend exibe.

| # | Item da Matriz | Path real | Endpoint(s) backend | 3Studio | Vendedor | Motorista | Clicheria | Regra de escopo (◐) | RLS tabela(s) | Camada UI |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Login | `/login` | público | ● | ● | ● | ● | — | — (rota pública) | **bypass middleware RBAC** |
| 2 | Dashboard | `/dashboard` | `GET /api/v1/provas/dashboard` | ● | ● | ● | ● | (contadores filtram pelo escopo de "Listagem de Provas") | `provas_digitais` (SELECT — já existe) | guarda só de auth, contadores limitados pelo backend |
| 3 | Listagem de Provas | `/provas` | `GET /api/v1/provas/` | ● | ◐ vendedor: `vendedor_id = self.id` | ◐ motorista: `status IN (COM_MOTORISTA*)` | ● | Vendedor: own only · Motorista: status "Em Trânsito" · Clicheria: full (Matriz exige ●) | `provas_digitais.SELECT` | `useAuthorization("provas.list").scope` controla filtros visíveis |
| 4 | Visualização de Prova (detalhe) | `/provas/[id]` | `GET /api/v1/provas/{id}` + `/imagem-url` + `/movimentacoes` + `/etiqueta.pdf` + `/qr-code.png` | ● | ◐ id ∈ provas próprias | ◐ id ∈ provas em trânsito (qualquer COM_MOTORISTA*) | ● | Mesmo escopo de #3 | `provas_digitais.SELECT` + `etiquetas.SELECT` + `movimentacoes.SELECT` | guarda de página + 404 silencioso se fora do escopo |
| 5 | Timeline da Prova | embutida em `/provas/[id]` | `GET /api/v1/provas/{id}/movimentacoes` | ● | ◐ same | ◐ same | ● | Mesmo escopo de #3/#4 | `movimentacoes.SELECT` | nenhum guard adicional (componente filho) |
| 6 | Criar Prova | `/nova-prova` | `POST /api/v1/provas/upload-url` + `POST /api/v1/provas/` | ● | ○ | ○ | ○ | — | `provas_digitais.INSERT` (admin only) | guard de página `useAuthorization("provas.create")` |
| 7 | Escanear QR Code | `/escanear` | `POST /api/v1/provas/scan` + `POST /api/v1/provas/{id}/transicoes` | ● | ● | ● | ● | (a permissão de transição depende de state-machine, não da Matriz) | `provas_digitais.SELECT` (lookup) + `movimentacoes.INSERT` | nenhum guard — universal |
| 8 | Cadastro de Usuários | `/usuarios` | `GET/POST/PATCH/DELETE /api/v1/users/*` | ● | ○ | ○ | ○ | — | `usuarios.SELECT/INSERT/UPDATE` (admin) | guard de página + ocultar "Novo usuário" |
| 9 | Relatórios | `/relatorios` | `GET /api/v1/reports` + `GET /api/v1/reports/export` | ● | ○ | ○ | ○ | — | `provas_digitais` + `movimentacoes` (lidas via service_role; sem nova policy) | guard proativo (substitui o reativo) |
| 10 | Configurações do Sistema | `/configuracoes` | `GET/PATCH /api/v1/configuracoes` | ● | ○ | ○ | ○ | — | `configuracoes_sistema.SELECT/UPDATE` (admin) | guard de página |
| 11 | Log de Auditoria | `/auditoria` | `GET /api/v1/audit-log/*` | ● | ○ | ○ | ○ | — | `audit_logs.SELECT` (admin) | guard de página (já existe) |
| 12 | Reiniciar Ciclo (Reprovação) | ação dentro de `/provas/[id]` | `POST /api/v1/provas/{id}/reiniciar-ciclo` | ● | ○ | ○ | ○ | — | `provas_digitais.UPDATE` (admin) + `movimentacoes.INSERT` | botão escondido em `<AdminActions>` |
| 13 | Cancelar Prova | ação dentro de `/provas/[id]` | `POST /api/v1/provas/{id}/cancelar` | ● | ○ | ○ | ○ | — | `provas_digitais.UPDATE` (admin) + `movimentacoes.INSERT` | botão escondido em `<AdminActions>` |

### 3.1 Página inicial por perfil (RF-021 — redirect em caso de 403)

| Perfil | Página inicial proposta | Justificativa |
|---|---|---|
| 3Studio | `/dashboard` | Visão consolidada (admin precisa ver tudo). |
| Vendedor | `/dashboard` | Vê apenas seus contadores, mas é a primeira tela útil. |
| Motorista | `/escanear` | Atividade primária do motorista é escanear o QR; dashboard é secundário. |
| Clicheria | `/dashboard` | Visão completa do que está chegando. |

> **Decisão proposta:** alinhar com a tela mais "ativa" por perfil. Para
> Motorista, escanear é o uso primário (é o ator de quase todas as
> transições). Para os outros, dashboard. Decisão registrada também no
> Gate 2 dentro do `DECISIONS.md`. **Reportar discordância** se o
> solicitante preferir `/dashboard` para todos.

### 3.2 Cobertura — checklist de células

- ●/◐/○ = 13 linhas × 4 perfis = **52 células**.
- ● = 27 · ◐ = 5 · ○ = 20.
- 100% das 52 células serão cobertas em testes de integração (Seção 9).

### 3.3 Mudanças necessárias na RLS atual (preview)

- **Adicionar SELECT em `etiquetas` para Motorista** (status COM_MOTORISTA) e **Clicheria** (status clicheria-states). Hoje é só admin + vendedor. Migration RLS 009.
- **Outros recursos:** policies já existentes cobrem o necessário. Apenas reformatar/renomear se conveniente (sem deletar policies funcionando).

---

## 4. Desenho de `access-matrix.ts`

Esboço (NÃO implementação). Ver Seção 5 para referência cruzada com o
middleware.

```typescript
// frontend/src/lib/access-matrix.ts
// Fonte única de verdade do RBAC. Espelhada por:
//   - middleware.ts (camada superior)
//   - backend/app/access/matrix.py (geração paralela; ver ADR proposto)
//   - migrations/rls/009_*.sql (camada inferior)
//
// Toda alteracao desta tabela exige PR cobrindo as TRES camadas.

export type Setor = "STUDIO" | "VENDEDOR" | "MOTORISTA" | "CLICHERIA";
export type Acesso = "full" | "parcial" | "negado";

export type EscopoFiltro =
  | { kind: "none" }                        // ● ou ○
  | { kind: "self_vendedor" }               // vendedor: vendedor_id == user.id
  | { kind: "status_motorista_em_transito" } // motorista: status IN (COM_MOTORISTA, ...)
  | { kind: "status_clicheria" };            // clicheria: status IN (ENVIADA_PARA_CLICHERIA, ENCAMINHADA_A_CLICHERIA, RECEBIDA_PELA_CLICHERIA)

export interface PerfilAcesso {
  acesso: Acesso;
  escopo: EscopoFiltro;
}

export interface AccessRule {
  /** Nome curto, kebab-case (ex.: 'provas.list'). Chave usada por enforce_access_for / useAuthorization. */
  key: string;
  /** Path do App Router que dispara a checagem do middleware. Strings literais (não regex). */
  path: string;
  /** Match do path: 'exact' (path igual) | 'prefix' (path começa com) | 'dynamic' (segmento dinâmico [id]). */
  match: "exact" | "prefix" | "dynamic";
  /** Predicado por perfil (3Studio = is_admin). */
  perfis: {
    studio_admin: PerfilAcesso;     // 3Studio = is_admin=true
    vendedor: PerfilAcesso;
    motorista: PerfilAcesso;
    clicheria: PerfilAcesso;
  };
}

/**
 * Página inicial por perfil — usada nos redirects 302 do middleware
 * quando acesso é negado.
 */
export const HOME_BY_PROFILE: Record<keyof AccessRule["perfis"], string> = {
  studio_admin: "/dashboard",
  vendedor: "/dashboard",
  motorista: "/escanear",
  clicheria: "/dashboard",
};

/**
 * 13 entradas + ações administrativas embutidas em /provas/[id].
 * O array é a ordem de avaliação — paths mais específicos primeiro.
 */
export const ACCESS_MATRIX: AccessRule[] = [
  { key: "login", path: "/login", match: "prefix", perfis: { studio_admin: PA.full(), vendedor: PA.full(), motorista: PA.full(), clicheria: PA.full() } },

  { key: "dashboard", path: "/dashboard", match: "exact", perfis: { studio_admin: PA.full(), vendedor: PA.full(), motorista: PA.full(), clicheria: PA.full() } },

  { key: "provas.create", path: "/nova-prova", match: "exact", perfis: { studio_admin: PA.full(), vendedor: PA.deny(), motorista: PA.deny(), clicheria: PA.deny() } },

  { key: "provas.list", path: "/provas", match: "exact", perfis: {
      studio_admin: PA.full(),
      vendedor:    PA.parcial("self_vendedor"),
      motorista:   PA.parcial("status_motorista_em_transito"),
      clicheria:   PA.full() } },

  { key: "provas.detail", path: "/provas/[id]", match: "dynamic", perfis: {
      studio_admin: PA.full(),
      vendedor:    PA.parcial("self_vendedor"),
      motorista:   PA.parcial("status_motorista_em_transito"),
      clicheria:   PA.full() } },

  { key: "scanner", path: "/escanear", match: "prefix", perfis: { studio_admin: PA.full(), vendedor: PA.full(), motorista: PA.full(), clicheria: PA.full() } },

  { key: "usuarios", path: "/usuarios", match: "prefix", perfis: { studio_admin: PA.full(), vendedor: PA.deny(), motorista: PA.deny(), clicheria: PA.deny() } },

  { key: "relatorios", path: "/relatorios", match: "prefix", perfis: { studio_admin: PA.full(), vendedor: PA.deny(), motorista: PA.deny(), clicheria: PA.deny() } },

  { key: "configuracoes", path: "/configuracoes", match: "prefix", perfis: { studio_admin: PA.full(), vendedor: PA.deny(), motorista: PA.deny(), clicheria: PA.deny() } },

  { key: "auditoria", path: "/auditoria", match: "prefix", perfis: { studio_admin: PA.full(), vendedor: PA.deny(), motorista: PA.deny(), clicheria: PA.deny() } },

  // Ações administrativas dentro do detalhe — usadas pelo useAuthorization,
  // não pelo middleware (não correspondem a paths exclusivos).
  { key: "provas.cancel",  path: "(action)", match: "exact", perfis: { studio_admin: PA.full(), vendedor: PA.deny(), motorista: PA.deny(), clicheria: PA.deny() } },
  { key: "provas.restart", path: "(action)", match: "exact", perfis: { studio_admin: PA.full(), vendedor: PA.deny(), motorista: PA.deny(), clicheria: PA.deny() } },
];

// helper PA (PerfilAcesso) — produz objetos imutáveis sem boilerplate
const PA = {
  full: (): PerfilAcesso => ({ acesso: "full",   escopo: { kind: "none" } }),
  deny: (): PerfilAcesso => ({ acesso: "negado", escopo: { kind: "none" } }),
  parcial: (kind: EscopoFiltro["kind"]): PerfilAcesso => ({ acesso: "parcial", escopo: { kind } as EscopoFiltro }),
};

export function getRuleForPath(pathname: string): AccessRule | null { /* exact/prefix/dynamic match */ }
export function resolveProfile(user: { is_admin: boolean; setor: Setor } | null): keyof AccessRule["perfis"] | null { /* is_admin → studio_admin; senão setor lowercase */ }
export function evaluate(rule: AccessRule, user: { is_admin: boolean; setor: Setor }): PerfilAcesso { /* ... */ }
```

### 4.1 Compartilhamento backend × frontend

**Decisão proposta:** **duplicação controlada com gerador**. O TS é a fonte;
um pequeno script Python (`scripts/gen_access_matrix_py.py`) lê o TS e
emite `backend/app/access/matrix.py` com as mesmas regras, num formato
Python-puro (Pydantic/dataclass). O CI roda o gerador e quebra se
`matrix.py` ficar fora de sincronia. **Justificativa:**

- Endpoint REST que devolve a matriz funcionaria mas adiciona round-trip
  e dependência runtime entre backend e frontend.
- Geração paralela (ler manualmente nas duas pontas) introduz drift —
  classe de bug que a wave inteira existe para evitar.
- Gerador one-shot mantém o TS como SSoT, dá ao backend tipos estáticos,
  e custa ~50 linhas de Python.

**Alternativa registrada para consideração no Gate 2:** YAML único em
`shared/access-matrix.yaml`, lido pelos dois lados. Mais higiênico, mas
exige um leitor de YAML com tipagem em TS (overhead). Decisão final fica
para o Gate 2 com base em concordância do solicitante.

### 4.2 Helpers backend

```python
# backend/app/access/__init__.py
# exporta:
#   ACCESS_MATRIX (lista de AccessRule, espelhada do TS pelo gerador)
#   resolve_profile(user) -> Profile  (admin > setor)
#   enforce_access_for(rule_key, user) -> raises HTTPException(302/403)
#   scope_filter_for(rule_key, user) -> SQL clause | None  (substitui _scoping_filter)
```

---

## 5. Desenho do middleware

Arquivo único `frontend/src/middleware.ts` (já existe; será reescrito).

```typescript
// (esboço — não implementação)
import { NextResponse, type NextRequest } from "next/server";
import { updateSession, getUserSetorAndAdmin } from "@/lib/supabase/middleware";
import { ACCESS_MATRIX, HOME_BY_PROFILE, getRuleForPath, resolveProfile, evaluate } from "@/lib/access-matrix";

const PUBLIC_PATHS = ["/login", "/_next", "/api/health", "/favicon.ico"];

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // (1) Public paths — pass-through (sem refresh de sessao para /api/health).
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next({ request });
  }

  // (2) Refresh de sessao Supabase + redirect /login se nao autenticado.
  //     updateSession ja faz isso hoje; manter.
  const sessionResponse = await updateSession(request);
  if (sessionResponse.status === 302 || sessionResponse.status === 307) return sessionResponse;

  // (3) Carregar perfil do usuario (chamada minima — apenas is_admin + setor).
  //     Implementacao: cookie de sessao Supabase ja carrega o JWT;
  //     buscamos os campos `is_admin` e `setor` em `public.usuarios` por
  //     auth_uid. Para evitar query a cada request, manter cache em
  //     memoria (LRU) por 30s usando o `auth_uid` como chave (HMR-safe).
  const profile = await getUserSetorAndAdmin(request);
  if (!profile) {
    // sem perfil cadastrado em public.usuarios -> redirect para /login
    return redirectToLogin(request, "perfil_ausente");
  }

  // (4) Localizar regra na matriz.
  const rule = getRuleForPath(pathname);
  if (!rule) {
    // Path nao mapeado: politica conservadora -> negado.
    return redirectWithToast(request, profile, "rota_nao_mapeada");
  }

  // (5) Avaliar acesso.
  const decision = evaluate(rule, profile);
  if (decision.acesso === "negado") {
    return redirectWithToast(request, profile, "rota_negada");
  }

  // (6) Acesso parcial: injeta header com hint de escopo p/ os handlers.
  const response = NextResponse.next({ request });
  if (decision.acesso === "parcial") {
    response.headers.set("x-rbac-scope", JSON.stringify({ kind: decision.escopo.kind, user_id: profile.user_id }));
  }
  return response;
}

function redirectWithToast(request: NextRequest, profile, reason: string) {
  const home = HOME_BY_PROFILE[resolveProfile(profile)] ?? "/dashboard";
  const url = request.nextUrl.clone();
  url.pathname = home;
  url.search = "";
  const res = NextResponse.redirect(url, 302);
  // cookie efemero (max-age=10s, httpOnly=false) para que o frontend leia e renderize um toast
  res.cookies.set("auth-toast", JSON.stringify({ kind: reason, ts: Date.now() }), {
    httpOnly: false, sameSite: "lax", path: "/", maxAge: 10,
  });
  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
```

### 5.1 Fluxo de mensagens

- Acesso negado → `redirectWithToast(reason='rota_negada')` → frontend lê
  cookie `auth-toast`, exibe toast (Wave 6 `<Toaster>` quando integrado;
  por agora um banner simples) e remove o cookie via JS.
- JWT expirado → fluxo do Supabase já existente redireciona para `/login`.
- Perfil sumiu da BD (deletado por outro admin) → `redirect /login` com
  cookie `auth-toast='perfil_ausente'`.

### 5.2 Custo de uma checagem

- **1 query SQL adicional por request** (busca `setor`/`is_admin` em
  `usuarios` por `auth_uid`). Mitigação: LRU em memória (TTL 30s) — o
  middleware roda em runtime serverless do Next/Vercel, então o cache é
  por instância. Aceitável: na prática, requests do mesmo usuário em
  sequência ficam na mesma instância por cache de afinidade.
- **Alternativa (registrada, NÃO escolhida):** decodificar JWT
  diretamente no middleware **se** colocarmos `setor`/`is_admin` no JWT
  via Custom Access Token Hook do Supabase. **Fora do escopo da Wave 1
  v4.0** — toca configuração do Auth.

---

## 6. Desenho das políticas RLS

### 6.0 Padrão de leitura do perfil

**Decisão proposta** (a registrar em `DECISIONS.md` no Gate 2):

> Manter o padrão atual `EXISTS (SELECT 1 FROM usuarios u WHERE
> u.auth_uid = (SELECT auth.uid()) AND ...)` em todas as policies novas.
> Essa abordagem **diverge do exemplo do DAT v3.0 Seção 7.2** (que sugere
> `auth.jwt() ->> 'setor'`), e a divergência é intencional:
> 1. O JWT do Supabase Auth hoje **não tem** o claim `setor` (validado
>    via MCP). Adicioná-lo exige Custom Access Token Hook na config do
>    Auth — fora do escopo da Wave 1 v4.0.
> 2. As 12 policies existentes já estão otimizadas com `(SELECT
>    auth.uid())` (ADR-029); usar o mesmo padrão evita duas convenções
>    coexistindo.
> 3. A `usuarios` tem índice em `auth_uid` (UNIQUE) — lookup é O(log n).

> **Para reduzir repetição** e facilitar manutenção, será criada uma SQL
> function helper:
>
> ```sql
> -- /backend/migrations/rls/009_helpers.sql (proposta)
> CREATE OR REPLACE FUNCTION current_user_is_admin() RETURNS boolean
>   LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
>     SELECT COALESCE((SELECT u.is_admin FROM public.usuarios u
>                      WHERE u.auth_uid = (SELECT auth.uid())), false);
> $$;
> CREATE OR REPLACE FUNCTION current_user_setor() RETURNS public.setor_enum
>   LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
>     SELECT u.setor FROM public.usuarios u WHERE u.auth_uid = (SELECT auth.uid());
> $$;
> CREATE OR REPLACE FUNCTION current_user_id() RETURNS uuid
>   LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
>     SELECT u.id FROM public.usuarios u WHERE u.auth_uid = (SELECT auth.uid());
> $$;
> REVOKE EXECUTE ON FUNCTION current_user_is_admin(), current_user_setor(), current_user_id() FROM PUBLIC;
> GRANT  EXECUTE ON FUNCTION current_user_is_admin(), current_user_setor(), current_user_id() TO authenticated;
> ```
>
> Essas funções não mudam o vínculo lógico — fazem o mesmo SELECT de
> antes, mas dão clareza à expressão das policies.

### 6.1 Policies a CRIAR / SUBSTITUIR

> Lista das policies novas e substituições. **Não há DROP TABLE; apenas
> DROP POLICY IF EXISTS + CREATE POLICY** (idempotente — padrão dos
> arquivos `001-008` existentes).

**Arquivo `009_helpers.sql`** — funções helper (SQL acima).

**Arquivo `010_rebase_rls_v4.sql`** — reaplica TODAS as 12 policies
existentes com a mesma semântica, mas usando os helpers (legibilidade).
Estritamente NO-OP funcional (não muda quem vê o quê). Validado por
teste de equivalência antes/depois.

**Arquivo `011_etiquetas_select_motorista_clicheria.sql`** — fecha a
lacuna L-RLS-1 (Seção 2.3). Conteúdo SQL completo proposto:

```sql
-- /backend/migrations/rls/011_etiquetas_select_motorista_clicheria.sql
-- Wave 1 v4.0 — Componente 05 (atualizacao v4.0)
-- Objetivo: alinhar etiquetas.SELECT com a Matriz de Acesso (Seção 6 do
-- Requisitos v4.0). Hoje: admin + vendedor own. Depois: + motorista
-- (status COM_MOTORISTA*) + clicheria (status clicheria-states).
-- Sem isso, defesa em profundidade fica incompleta para o detalhe da
-- prova quando acessado por motorista/clicheria via Supabase client.

DROP POLICY IF EXISTS pol_etiquetas_select ON public.etiquetas;
CREATE POLICY pol_etiquetas_select ON public.etiquetas
  FOR SELECT TO public
  USING (
    public.current_user_is_admin()
    OR EXISTS (
      SELECT 1 FROM public.provas_digitais pd
      WHERE pd.id = etiquetas.prova_id
        AND (
          pd.vendedor_id = public.current_user_id()
          OR (
            public.current_user_setor() = 'MOTORISTA'::public.setor_enum
            AND pd.status = 'COM_MOTORISTA'::public.status_prova_enum
          )
          OR (
            public.current_user_setor() = 'CLICHERIA'::public.setor_enum
            AND pd.status = ANY (ARRAY[
              'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,
              'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,
              'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum
            ])
          )
        )
    )
  );
```

> **Nota sobre Wave 3 v4.0:** quando os 3 contextos `COM_MOTORISTA_*`
> entrarem no enum, esta policy precisará ser reaplicada substituindo
> `'COM_MOTORISTA'::status_prova_enum` por `IN (COM_MOTORISTA_IDA_LAMINACAO,
> COM_MOTORISTA_VOLTA_LAMINACAO, COM_MOTORISTA_ENTREGA_FINAL)`. Wave 1 v4.0
> não toca — só Wave 3 v4.0 toca.

### 6.2 Policies a MANTER intactas

| Policy | Motivo |
|---|---|
| `pol_audit_select` | Já é admin-only via helper. |
| `pol_config_select` / `pol_config_update` | Já são admin-only. |
| `pol_provas_insert` / `pol_provas_update` | Já são admin-only (matriz = ●/○). |
| `pol_provas_select` | Já cobre admin + vendedor + motorista + clicheria. |
| `pol_movimentacoes_insert` | Admin-only via state machine no backend (transição admin gera mov). |
| `pol_movimentacoes_select` | Já cobre os 4 perfis com escopos corretos. |
| `pol_usuarios_*` | self + admin é suficiente para a Matriz (usuários = ●/○). |

Policies serão **reescritas no formato com helpers** (em
`010_rebase_rls_v4.sql`), mas manterão a mesma semântica.

### 6.3 Resumo final RLS Wave 1 v4.0

- **3 arquivos SQL novos** em `/backend/migrations/rls/`:
  - `009_helpers.sql`
  - `010_rebase_rls_v4.sql` (NO-OP funcional; cosmético)
  - `011_etiquetas_select_motorista_clicheria.sql` (única alteração de comportamento — fecha L-RLS-1)
- **0 policies REMOVIDAS** (apenas REPLACED via DROP IF EXISTS + CREATE).
- **0 migrations Alembic** (sem alteração de schema de tabela).
- **0 GRANT/REVOKE novos** (a tripla camada de `audit_logs` já existe — RLS 008).

---

## 7. Desenho do hook `useAuthorization`

Arquivo: `frontend/src/lib/hooks/use-authorization.ts` (caminho usado pelo
prompt). Note: hoje o projeto usa `src/hooks/`. Para manter consistência
com o prompt e as decisões da v4.0, **proposta**: criar a pasta
`src/lib/hooks/` para utilitários ligados a `lib/` (como
`access-matrix.ts`) e manter `src/hooks/` para hooks de domínio (UI).
**Reportar** se preferir manter tudo em `src/hooks/`.

```typescript
// frontend/src/lib/hooks/use-authorization.ts
"use client";
import { useMemo } from "react";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { ACCESS_MATRIX, evaluate, resolveProfile } from "@/lib/access-matrix";
import type { AccessRule, EscopoFiltro } from "@/lib/access-matrix";

export interface AuthorizationResult {
  hasAccess: boolean;
  /** 'full' | 'parcial' | 'negado' */
  level: AccessRule["perfis"]["studio_admin"]["acesso"];
  /** Escopo aplicável quando level === 'parcial'. Indefinido caso contrário. */
  scope?: EscopoFiltro;
  /** True enquanto o useCurrentUser ainda esta carregando. */
  loading: boolean;
}

/**
 * Consulta a Matriz de Acesso para uma chave de regra (ex.: 'provas.list',
 * 'provas.cancel', 'auditoria'). Use em pages para guard proativo, em
 * componentes para esconder elementos, e em handlers de UI para enriquecer
 * filtros de query (ex.: vendedor so ve ?vendedor_id=self).
 */
export function useAuthorization(ruleKey: string): AuthorizationResult {
  const { user, loading } = useCurrentUser();

  return useMemo(() => {
    if (loading) return { hasAccess: false, level: "negado", loading: true };
    if (!user) return { hasAccess: false, level: "negado", loading: false };

    const rule = ACCESS_MATRIX.find(r => r.key === ruleKey);
    if (!rule) return { hasAccess: false, level: "negado", loading: false };

    const profile = resolveProfile(user);
    const decision = evaluate(rule, user);
    return {
      hasAccess: decision.acesso !== "negado",
      level: decision.acesso,
      scope: decision.acesso === "parcial" ? decision.escopo : undefined,
      loading: false,
    };
  }, [user, loading, ruleKey]);
}
```

### 7.1 Onde será consumido

| Página/Componente | Chamada | Comportamento |
|---|---|---|
| `(dashboard)/layout.tsx` (sidebar) | para cada item de nav: `useAuthorization(item.ruleKey).hasAccess` | esconde itens negados |
| `auditoria/page.tsx` | `useAuthorization("auditoria")` | guard proativo (substitui o atual) |
| `relatorios/page.tsx` | `useAuthorization("relatorios")` | promove de reativo a proativo |
| `usuarios/page.tsx` | `useAuthorization("usuarios")` | guard de página + esconde "Novo usuário" |
| `configuracoes/page.tsx` | `useAuthorization("configuracoes")` | guard de página |
| `nova-prova/page.tsx` | `useAuthorization("provas.create")` | guard de página |
| `provas/page.tsx` | `useAuthorization("provas.list")` | usa `.scope` para esconder filtro de vendedor (se scope = self_vendedor) |
| `provas/[id]/AdminActions.tsx` | `useAuthorization("provas.cancel")` + `useAuthorization("provas.restart")` | esconde botões |
| `useGlobalShortcuts.ts` | itera `ACCESS_MATRIX` em vez de hardcode | filtra `g r`/`g a` automaticamente |
| `<Restricted />` (novo) | recebe `ruleKey` opcional | renderiza mensagem padrão "Acesso restrito (RNF-007)" + botão para `HOME_BY_PROFILE[perfil]` |

### 7.2 Comportamento ao montar

1. `useCurrentUser()` continua sendo a fonte do `is_admin`/`setor` no
   frontend (`/api/v1/users/me`).
2. Hook lê o resultado, consulta a `ACCESS_MATRIX` por `ruleKey`,
   resolve o perfil (admin > setor) e devolve `{ hasAccess, level, scope, loading }`.
3. Enquanto `loading=true`, os componentes **não devem renderizar nada**
   ou renderizar skeleton — **nunca** assumir `hasAccess=true` antes do
   load. Isso evita flash de UI proibida.

---

## 8. Plano de migração das chamadas existentes (refactor coordenado)

### 8.1 Backend (FastAPI) — substituições autorizadas

> Cada linha = um commit `refactor(wave1-v4/c05): ...`.

| ID | Arquivo | Ação | Antes | Depois |
|----|---|---|---|---|
| B1 | `app/api/deps.py` | Manter `get_admin_user` como helper legacy. | — | Adicionar comentário "Use `enforce_access_for(rule_key, user)` para novos endpoints." |
| B2 | `app/api/deps.py` | Remover `require_role` (factory nunca usado). | linhas 107–120 | (deletado) |
| B3 | `app/access/__init__.py` | **Adicionar** `enforce_access_for(rule_key, user)` que consulta `matrix.py` e levanta `HTTPException(403)` em caso de negação. | (novo) | (novo) |
| B4 | `app/access/scopes.py` | **Adicionar** `scope_filter_for(rule_key, user)` retornando cláusula SQLAlchemy. Substitui `_scoping_filter` (atualmente em `provas.py`). | (novo) | (novo) |
| B5 | `app/api/v1/provas.py` | Substituir todas as ocorrências de `_scoping_filter(user)` por `scope_filter_for("provas.list", user)`. | linhas 660–676 e usos | usa o helper acima. |
| B6 | `app/api/v1/provas.py` | `Depends(get_admin_user)` em POST `/`, POST `/upload-url`, POST `/cancelar`, POST `/reiniciar-ciclo` → substituir por `Depends(get_current_user)` + `enforce_access_for("provas.create" / "provas.cancel" / "provas.restart", user)`. | endpoints citados | mudança de 1 linha por endpoint. |
| B7 | `app/api/v1/configuracoes.py` | Mesmo padrão de B6 com chave `configuracoes`. | 48, 91, 150 | — |
| B8 | `app/api/v1/audit_log.py` | Mesmo padrão com chave `auditoria`. | 126, 228, 290 | — |
| B9 | `app/api/v1/reports.py` | Mesmo padrão com chave `relatorios`. | 1073, 1159 | — |
| B10 | `app/api/v1/users.py` | A checagem `if not is_admin and current_user.id != user.id: 403` permanece (não é célula da Matriz; é invariante "self ou admin"). Documentar comentário inline com referência à Matriz (linha "Cadastro de Usuários" cobre apenas admin). | 192–193 | comentário adicionado. |
| B11 | `app/api/v1/users.py` | Demais endpoints (POST/GET/PATCH/DELETE) substituem `Depends(get_admin_user)` por `enforce_access_for("usuarios", user)`. | 66, 133, 205, 353 | — |
| B12 | `app/services/state_machine.py` | **Não tocar.** Validações de cancelamento/setor são regra de negócio; a Matriz é regra de página. | — | — |

### 8.2 Frontend (Next.js) — substituições autorizadas

| ID | Arquivo | Ação |
|----|---|---|
| F1 | `src/middleware.ts` + `src/lib/supabase/middleware.ts` | Reescrever conforme Seção 5. Manter `updateSession` como helper interno chamado pelo novo middleware. |
| F2 | `src/app/(dashboard)/layout.tsx` | Substituir filtragem manual por map de `MAIN_NAV/SECONDARY_NAV` adicionando `ruleKey`; render usa `useAuthorization(item.ruleKey).hasAccess`. |
| F3 | `src/hooks/useGlobalShortcuts.ts` | Substituir `SHORTCUT_DEFS` hardcode por leitura de `ACCESS_MATRIX` filtrado para regras com path navegável + adicionar campo `shortcut?: string`. |
| F4 | `src/app/(dashboard)/auditoria/page.tsx` | Substituir guard `if (!me.is_admin)` por `useAuthorization("auditoria")` + `<Restricted />`. |
| F5 | `src/app/(dashboard)/relatorios/page.tsx` | Substituir guard reativo por proativo via `useAuthorization("relatorios")`. |
| F6 | `src/app/(dashboard)/usuarios/page.tsx` | Adicionar guard de página + ocultar "Novo usuário" via `useAuthorization("usuarios")`. |
| F7 | `src/app/(dashboard)/configuracoes/page.tsx` | Adicionar guard de página via `useAuthorization("configuracoes")`. |
| F8 | `src/app/(dashboard)/nova-prova/page.tsx` | Adicionar guard de página via `useAuthorization("provas.create")`. |
| F9 | `src/app/(dashboard)/provas/page.tsx` | Substituir lógica `me.is_admin === true` por `useAuthorization("provas.list").level === "full"`. |
| F10 | `src/app/(dashboard)/provas/[id]/AdminActions.tsx` | Substituir `if (!user.is_admin) return null` por `useAuthorization("provas.cancel")/("provas.restart")`. |
| F11 | `src/components/Restricted.tsx` | **Novo componente** reutilizável — exibe "Acesso restrito" + botão para `HOME_BY_PROFILE[perfil]`. |
| F12 | `src/lib/types/usuario.ts` | Estender `UserInfo.setor` para union literal: `"STUDIO" \| "VENDEDOR" \| "MOTORISTA" \| "CLICHERIA"`. |
| F13 | `src/middleware.ts` (post-redirect) | Adicionar leitura do cookie `auth-toast` no `<Toaster>`/banner do layout — exibe a mensagem e remove o cookie. |

### 8.3 Lint + grep final (proibitivo no CI)

Adicionar 3 regras `eslint-no-restricted-syntax` (frontend) e 3 grep checks
(backend) no CI:

| Regra | Ferramenta | Cenário proibido |
|---|---|---|
| `no-direct-is-admin-condition` | eslint custom | `user?.is_admin === ...` ou `user.is_admin` em components/pages — exceto em `useAuthorization` e em `useCurrentUser`. |
| `no-direct-setor-condition` | eslint custom | `user.setor === "..."` em pages/components — exceto `useAuthorization` e `useCurrentUser`. |
| `no-deps-get-admin-user` | grep CI | `Depends(get_admin_user)` ainda usado em endpoints novos (excluído `users.py` self check, que tem comentário documentando a invariante). |
| `no-require-role` | grep CI | qualquer uso de `require_role` deve falhar (factory removido). |
| `no-scoping-filter-direct` | grep CI | `_scoping_filter` em outros lugares que não `app/access/scopes.py`. |
| `matrix-coverage` | pytest custom | toda regra em `ACCESS_MATRIX` tem teste de equivalência associado (Seção 9). |

---

## 9. Estratégia de testes

> Referência cruzada com **DAT v3.0 Seção 3** (3 camadas de teste, ≥ 80%
> domínio/serviço, **≥ 95% na máquina de estados** — esta wave NÃO toca
> state machine, mas mantém o gate).

### 9.1 Unitários (pytest + jest)

#### Backend (`backend/tests/`)

| Arquivo | Cobre |
|---|---|
| `tests/access/test_matrix_structure.py` (novo) | Cada regra de `ACCESS_MATRIX` tem `path`, `match`, e os 4 perfis. Toda regra tem 4 entradas em `perfis`. Total de células = 13×4 = 52. |
| `tests/access/test_resolve_profile.py` (novo) | `resolve_profile(user)` devolve `studio_admin` quando `is_admin=True` (independente de setor); senão lowercase do setor. Edge: `STUDIO + is_admin=False` → `studio` (falla — não está na matriz; helper deve retornar None ou default seguro `null` → leva a `acesso='negado'`). |
| `tests/access/test_enforce_access_for.py` (novo) | Para cada (regra, perfil): célula `●` → no exception. Célula `○` → `HTTPException(403)`. Célula `◐` → no exception (escopo é responsabilidade do query). |
| `tests/access/test_scope_filter_for.py` (novo) | Para "provas.list" + vendedor → cláusula SQL inclui `vendedor_id == user.id`. Para "provas.list" + motorista → status IN COM_MOTORISTA. Para clicheria → IN clicheria-states. Para admin → None (sem restrição). |
| `tests/test_users_api.py` (existente) | Atualizar — endpoints continuam admin-only mas agora via `enforce_access_for`. |
| `tests/test_provas_api.py` (existente) | Atualizar — sem mudança semântica esperada. |
| `tests/test_configuracoes_api.py` (existente) | Atualizar — sem mudança semântica esperada. |

#### Frontend (`frontend/__tests__/`)

| Arquivo | Cobre |
|---|---|
| `__tests__/access-matrix.test.ts` | Mesma estrutura do backend (paridade). Importante: comparar com o output do gerador `gen_access_matrix_py.py` para garantir SSoT. |
| `__tests__/use-authorization.test.tsx` | Hook com mock de `useCurrentUser` para cada perfil + cada regra. |
| `__tests__/middleware.test.ts` | Para cada (perfil, path), o middleware ou passa, ou redireciona com cookie `auth-toast`. |

### 9.2 Integração (pytest + httpx AsyncClient + banco isolado)

Arquivo principal: `backend/tests/access/test_matrix_integration.py`.

| Cenário | Cobertura |
|---|---|
| **Status HTTP por (perfil, página)** | Para cada uma das 52 células: simula request HTTP autenticado + path → espera 200 (●), 200 + filtro de escopo (◐), 302 (○ via middleware) ou 403 (○ via API direto sem middleware). |
| **RLS por (perfil, tabela)** | Conexão como `authenticated` impersonando cada `auth_uid`: query direta a `provas_digitais`, `movimentacoes`, `etiquetas`, `audit_logs`, `configuracoes_sistema`, `usuarios`. Linhas retornadas devem bater com a Matriz. |
| **Equivalência middleware ↔ RLS (CRÍTICO)** | Para cada célula `○` da Matriz: middleware redireciona E RLS retorna 0 linhas via query direta. Para cada `●`: middleware passa E RLS retorna ≥ 1 linha. Para cada `◐`: middleware passa E RLS retorna apenas linhas no escopo. **Este é o teste que mitiga o risco crítico do Backlog v4.0 Seção 6.** |
| **Smoke do refactor: regressão zero** | Reaplicar todos os testes existentes pré-refactor (Wave 0–6 v3.0) — a cobertura atual de 724 testes não pode regredir. Wave 1 v4.0 deve **manter 724 + adicionar testes novos**. |
| **Idempotência das migrations RLS** | Aplicar `009 + 010 + 011`, depois `DROP POLICY` e reaplicar — sem erro. |

### 9.3 E2E (Playwright)

> Mantida a estratégia da Wave 5 v3.0. Não há cenário Playwright pré-existente
> formal nesta base; criar suite mínima.

| Cenário | Cobertura |
|---|---|
| 4 perfis × páginas-chave | Login com cada perfil → tenta `/dashboard`, `/provas`, `/nova-prova`, `/escanear`, `/relatorios`, `/auditoria`, `/usuarios`, `/configuracoes`. Espera redirect + toast quando negado, render normal quando permitido. |
| Toast de redirect | Cookie `auth-toast` é lido e renderiza mensagem padrão. |
| `/provas/[id]` fora do escopo | Vendedor tenta acessar `/provas/<prova-de-outro-vendedor>` → redirect + toast. |
| Atalhos de teclado | Usuário não-admin pressiona `g r` — nada acontece (ok). Usuário admin pressiona `g r` — navega para `/relatorios`. |

### 9.4 Meta de cobertura

- **≥ 80%** nas camadas `app/access/*` e `app/services/*` (módulos críticos da wave).
- **100% das 52 células** cobertas em testes de integração.
- **0% regressão** nos 724 testes existentes (Wave 6 closeout).

---

## 10. Migrations previstas

| Tipo | Arquivo | Conteúdo | Reversível? |
|---|---|---|---|
| Alembic | — | **Nenhuma migration Alembic nesta wave** (sem alteração de schema de tabela). | n/a |
| RLS | `backend/migrations/rls/009_helpers.sql` | `CREATE OR REPLACE FUNCTION` para 3 helpers (admin, setor, id) + REVOKE/GRANT. | Sim (DROP FUNCTION). |
| RLS | `backend/migrations/rls/010_rebase_rls_v4.sql` | `DROP POLICY IF EXISTS` + `CREATE POLICY` para todas as 12 policies existentes, agora usando helpers. **NO-OP funcional.** | Sim (reaplicar 005/006). |
| RLS | `backend/migrations/rls/011_etiquetas_select_motorista_clicheria.sql` | `DROP POLICY IF EXISTS pol_etiquetas_select` + `CREATE POLICY` cobrindo motorista (status COM_MOTORISTA) e clicheria (status clicheria-states). **Única alteração de comportamento.** | Sim (reaplicar 005). |

### 10.1 Garantias

- **Sem `DROP TABLE`.**
- **Sem `ALTER COLUMN` destrutivo.**
- **Sem renomeação de colunas.**
- **Idempotência:** todos os arquivos seguem o padrão `DROP IF EXISTS + CREATE` (igual aos existentes 001–008).
- **Reversibilidade:** rollback testado aplicando-se 005/006 originais por cima.

### 10.2 Aplicação

Executar via `python backend/migrations/rls/apply_rls.py` (script existente, suporta novos arquivos). **Não usar painel Supabase** (regra do projeto: tudo versionado).

---

## 11. Riscos e pontos de atenção

| ID | Risco | Severidade | Mitigação |
|----|---|---|---|
| **R-1** | **Inconsistência entre `access-matrix.ts` e RLS** (risco crítico documentado no Backlog v4.0 Seção 6). Atualização parcial pode permitir acesso indevido ou bloquear acesso legítimo. | **Crítica** | (a) Gerador `scripts/gen_access_matrix_py.py` impede drift backend × frontend. (b) Teste **automatizado de equivalência** (Seção 9.2) cobre as 52 células. (c) Checklist de PR obrigando atualização sincronizada das 3 camadas (TS + Python + RLS). |
| **R-2** | Quebra de funcionalidade existente ao remover checagens ad-hoc — algum caso de uso pode depender de uma condicional que parece RBAC mas é regra de negócio. | Alta | A Seção 8 lista cada checagem com classificação **manter/substituir**. As `RN-005`/`RN-010` e validações de transição **ficam intactas**. Toda substituição passa pelos 724 testes existentes; adicional: smoke E2E dos 4 perfis × páginas-chave. |
| **R-3** | Performance da RLS — cada policy faz EXISTS contra `usuarios`. Sem índice em `auth_uid` (já existe pela UNIQUE constraint), mas em volumes grandes pode pesar. | Baixa | (a) Índice em `usuarios.auth_uid` já é UNIQUE. (b) Helper `current_user_*()` é STABLE — Postgres pode cachear o valor por query. (c) ADR-029 já otimizou via `(SELECT auth.uid())`. (d) Para volumes futuros, considerar `auth.jwt() ->> 'setor'` via Custom Hook (fora desta wave). |
| **R-4** | JWT sem claims `setor`/`is_admin`. Se a v3.0 setasse isso no JWT, simplificaria as policies (ler do JWT é mais barato que EXISTS). | Bloqueador removido | Decisão da Seção 6.0: manter padrão atual. **Não consertar silenciosamente** — divergência com DAT v3.0 documentada em `DECISIONS.md` no Gate 2. |
| **R-5** | Condicional residual após o refactor — pode sobrar código morto (props passadas mas não usadas, imports). | Média | Lint + grep final (Seção 8.3) é parte do critério de aceitação 8 da Seção 5.3 do prompt. CI bloqueia se sobrar `if user.is_admin` ou `Depends(get_admin_user)` fora dos lugares ressalvados. |
| **R-6** | "Página inicial por perfil" — Motorista propõe-se em `/escanear` (não `/dashboard`). Pode quebrar expectativa do usuário existente. | Baixa | Decisão proposta (Seção 3.1) — pedir confirmação. Fallback seguro: deixar todos em `/dashboard` se solicitante preferir. |
| **R-7** | Cache LRU no middleware (TTL 30s) pode atrasar revogação de admin: se admin é desativado, ele continua tendo acesso por até 30s. | Baixa | (a) TTL curto (30s aceitável para UX). (b) `get_current_user` no backend continua validando `ativo=true` em cada request. (c) Endpoint sensível ainda é protegido pela RLS — `is_admin=false` na BD bloqueia mesmo se middleware estiver com cache obsoleto. |
| **R-8** | Custom Access Token Hook seria a solução elegante para colocar `setor` no JWT — mas requer config no Supabase Dashboard, fora do escopo. Adiar para Wave futura. | Informativo | Documentar como follow-up no `DECISIONS.md`. |
| **R-9** | Geração TS → Python pode falhar silenciosamente se o gerador tiver bug. | Baixa | CI roda `gen_access_matrix_py.py` e compara com arquivo commitado; falha se diff não-vazio. |
| **R-10** | A Wave 1 v4.0 não ataca a coluna `rota` (Wave 2 v4.0). Mas a Matriz menciona "rota selecionada" como filtro em `/provas` (RF-014). Frontend pode tentar usar uma coluna que ainda não existe. | Informativo | A Wave 1 v4.0 não adiciona o filtro de rota — apenas autoriza `/provas` por perfil. Wave 2 v4.0 adiciona o controle de filtro de rota em si. |
| **R-11** | **Risco de drift do middleware** — se o middleware faz cache de `setor`/`is_admin` mas o vendedor é promovido a admin, user precisa esperar até 30s para ver os elementos novos. | Baixa | TTL curto + invalidação manual via logout/login. Documentar no `CLAUDE.md`. |
| **R-12** | **Drawio v4.0 não foi lido** (item 8 da Seção 0). Pode haver detalhes em diagramas que afetem o desenho. | Médio | Gate 1 reporta isso explicitamente. **Reportar** ao solicitante se quer que a leitura seja feita antes do Gate 2. |

---

## Apêndice A — Frase exata para autorização

> Aguardando string **AUTORIZADO GATE 2 — WAVE 1 v4.0** para prosseguir.
