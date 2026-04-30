-- =============================================================================
-- RLS 011 (Wave 1 v4.0 — Componente 05): Estende pol_etiquetas_select para
-- motorista (status COM_MOTORISTA) e clicheria (status clicheria-states)
-- =============================================================================
-- IMPORTANTE: Este script e idempotente — DROP IF EXISTS antes de CREATE.
--
-- !!! SUPERSEDE POR 012 !!!
--   Esta migration referencia public.current_user_* — ver nota em 009. A 012
--   reaplica esta mesma policy referenciando app_private.current_user_*. O
--   estado final em producao e o da 012.
--
-- Contexto (analysis Secao 2.3 — lacuna L-RLS-1):
--   A Matriz de Acesso v4.0 (Secao 6 do RequisitosProvasDigitais_v4_0.docx)
--   exige que Motorista e Clicheria possam VISUALIZAR a prova de detalhe
--   (linha "Visualizacao de Prova (detalhe)" + "Timeline da Prova"), com
--   escopo restrito ao seu contexto operacional:
--     - Motorista: provas em transito (status = COM_MOTORISTA na v3.0;
--                  COM_MOTORISTA_* na v4.0 quando Wave 3 ampliar o enum).
--     - Clicheria: provas em status de clicheria (ENVIADA, ENCAMINHADA,
--                  RECEBIDA).
--
--   A pagina de detalhe carrega tambem a etiqueta (modal "Visualizar
--   etiqueta" + endpoint /etiqueta.pdf). Hoje:
--     - Backend usa service_role (bypassa RLS) e ja aplica scoping via
--       _carregar_prova_com_scoping em provas.py — funciona corretamente
--       para os 4 perfis.
--     - RLS de `etiquetas` cobre apenas admin + vendedor (RLS 005).
--
--   Defesa em profundidade incompleta: se motorista ou clicheria fizer
--   uma query direta a `etiquetas` via Supabase client (sessao
--   authenticated, nao service_role), nao verao etiquetas que
--   operacionalmente DEVEM ver. A regra RN-013 (defesa em duas camadas)
--   exige que essa lacuna seja fechada — feito aqui.
--
-- Comportamento depois da aplicacao:
--   - admin: ve todas as etiquetas (mesmo).
--   - vendedor: ve etiquetas das suas provas (mesmo).
--   - motorista: ve etiquetas de provas em status COM_MOTORISTA (NOVO).
--   - clicheria: ve etiquetas de provas em status de clicheria (NOVO).
--
-- Nota sobre Wave 3 v4.0: quando o enum status_prova_enum for ampliado
-- com COM_MOTORISTA_IDA_LAMINACAO / VOLTA_LAMINACAO / ENTREGA_FINAL,
-- esta policy precisara ser reaplicada substituindo
-- 'COM_MOTORISTA' pelo IN (...). Wave 1 v4.0 NAO toca o enum (Wave 3 v4.0
-- toca).
--
-- Validacao pos-aplicacao:
--   1. Como motorista impersonado em sessao authenticated:
--      SELECT count(*) FROM public.etiquetas e
--      JOIN public.provas_digitais p ON p.id = e.prova_id
--      WHERE p.status = 'COM_MOTORISTA';
--      -> deve retornar > 0 quando houver provas nesse status.
--   2. Como clicheria impersonada:
--      SELECT count(*) FROM public.etiquetas e
--      JOIN public.provas_digitais p ON p.id = e.prova_id
--      WHERE p.status IN ('ENVIADA_PARA_CLICHERIA','ENCAMINHADA_A_CLICHERIA','RECEBIDA_PELA_CLICHERIA');
--      -> deve retornar > 0 quando houver provas nesses status.
--   3. scripts/verify_rbac_equivalence.py: 0 desvios.
-- =============================================================================

DROP POLICY IF EXISTS pol_etiquetas_select ON public.etiquetas;
CREATE POLICY pol_etiquetas_select ON public.etiquetas
    FOR SELECT
    USING (
        public.current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM public.provas_digitais pd
            WHERE pd.id = etiquetas.prova_id
              AND (
                  -- vendedor ve etiquetas das suas provas
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
