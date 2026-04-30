-- =============================================================================
-- RLS 009 (Wave 1 v4.0 — Componente 05): Helpers SQL para policies
-- =============================================================================
-- IMPORTANTE: Este script e idempotente — CREATE OR REPLACE.
--
-- !!! SUPERSEDE POR 012 !!!
--   Esta migration cria 3 funcoes SECURITY DEFINER em `public`. Apos
--   aplicacao, o Supabase advisor reportou 6 WARN
--   (anon/authenticated_security_definer_function_executable) porque
--   `public` e exposto via PostgREST. A migration 012 move as funcoes
--   para um schema `app_private` fora do API exposto e remove as antigas
--   de `public`. Ao aplicar este arquivo do zero, em seguida aplique
--   tambem 010 (rebase) e 012 (move). 010 referencia public.* e 012 muda
--   tudo para app_private.* — o estado final e o de 012.
--
-- Contexto:
--   A Wave 1 v4.0 formaliza a Matriz de Acesso (Secao 6 do Requisitos
--   v4.0) como fonte unica de verdade espelhada em 4 camadas
--   (shared/access-matrix.json -> middleware Next + hook + backend +
--   policies RLS).
--
--   Para reduzir repeticao nas policies novas (RLS 010 e 011) e nas
--   reescritas das antigas (RLS 010 rebase), introduzimos 3 funcoes
--   helper que encapsulam a leitura do perfil da tabela `usuarios`
--   via auth_uid -> auth.uid().
--
--   Decisao registrada (analysis Secao 6.0 + DECISIONS.md proximo):
--   manter o padrao atual de subquery EXISTS contra `usuarios` em vez
--   do `auth.jwt() ->> 'setor'` proposto pelo DAT v3.0 Secao 7.2 — o
--   JWT do Supabase Auth atual nao tem o claim `setor` e adiciona-lo
--   exigiria Custom Access Token Hook na config do Supabase, fora do
--   escopo desta wave.
--
-- Padrao das funcoes:
--   - SECURITY DEFINER: a funcao roda com privilegio do owner (postgres),
--     o que permite ler `public.usuarios` mesmo a partir de uma sessao
--     authenticated que tenha RLS de `usuarios` restritiva.
--   - SET search_path = '': obrigatorio para SECURITY DEFINER (CVE-2018-1058).
--     ADR-024 ja aplica esse padrao a outras funcoes.
--   - STABLE: garante que o planner pode cachear o resultado dentro de uma
--     mesma query (importante para RLS chamada por linha).
--   - REVOKE FROM PUBLIC + GRANT TO authenticated: limita execucao a
--     sessoes autenticadas (anon nao deveria nem chamar).
--
-- Validacao pos-aplicacao:
--   1. Como sessao authenticated impersonando um admin:
--      SELECT public.current_user_is_admin(); -- deve retornar true
--      SELECT public.current_user_setor();   -- deve retornar 'STUDIO'
--   2. Como sessao authenticated impersonando vendedor:
--      SELECT public.current_user_is_admin(); -- deve retornar false
--      SELECT public.current_user_setor();   -- deve retornar 'VENDEDOR'
--   3. Como sessao SEM auth.uid() valido:
--      SELECT public.current_user_is_admin(); -- deve retornar false (COALESCE)
--      SELECT public.current_user_setor();   -- deve retornar NULL
-- =============================================================================


-- ─── Helper 1: current_user_is_admin() ─────────────────────────────────────
-- Retorna TRUE se o auth.uid() corrente corresponder a um usuario com
-- is_admin=true. COALESCE garante FALSE para sessoes sem auth (anon).
CREATE OR REPLACE FUNCTION public.current_user_is_admin()
    RETURNS boolean
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = ''
AS $$
    SELECT COALESCE((
        SELECT u.is_admin
        FROM public.usuarios u
        WHERE u.auth_uid = (SELECT auth.uid())
    ), false);
$$;


-- ─── Helper 2: current_user_setor() ────────────────────────────────────────
-- Retorna o setor enum do usuario corrente. NULL se nao houver match
-- (sessao anon, usuario nao cadastrado em public.usuarios).
CREATE OR REPLACE FUNCTION public.current_user_setor()
    RETURNS public.setor_enum
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = ''
AS $$
    SELECT u.setor
    FROM public.usuarios u
    WHERE u.auth_uid = (SELECT auth.uid());
$$;


-- ─── Helper 3: current_user_id() ───────────────────────────────────────────
-- Retorna o id (UUID, PK de public.usuarios) do usuario corrente. NULL se
-- nao houver match. Usado para policies que filtram por owner (vendedor_id,
-- usuario_id, etc.).
CREATE OR REPLACE FUNCTION public.current_user_id()
    RETURNS uuid
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = ''
AS $$
    SELECT u.id
    FROM public.usuarios u
    WHERE u.auth_uid = (SELECT auth.uid());
$$;


-- ─── Permissoes ────────────────────────────────────────────────────────────
-- Remove EXECUTE de PUBLIC e concede apenas a roles que devem chamar:
--   - authenticated: sessoes de usuarios logados via Supabase Auth.
--   - service_role: backend FastAPI (bypassa RLS, mas pode chamar helpers
--     se um dia precisar — ex.: testes de equivalencia).
-- anon nao pode chamar (nao tem auth.uid() valido de qualquer forma).
REVOKE EXECUTE ON FUNCTION public.current_user_is_admin() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.current_user_setor()    FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.current_user_id()       FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.current_user_is_admin() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.current_user_setor()    TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.current_user_id()       TO authenticated, service_role;
