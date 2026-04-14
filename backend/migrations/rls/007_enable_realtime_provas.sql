-- =============================================================================
-- 007_enable_realtime_provas.sql
-- Wave 4 — Componente 15 (Dashboard em Tempo Real)
--
-- Adiciona provas_digitais a publicacao supabase_realtime para que o
-- Supabase Realtime (WebSocket) emita eventos de INSERT/UPDATE nesta tabela.
-- O frontend assina estes eventos para atualizar os contadores do dashboard
-- sem necessidade de polling.
--
-- Somente provas_digitais e adicionada. Tabelas imutaveis (movimentacoes,
-- audit_logs, etiquetas) nao precisam de Realtime — as mudancas de status
-- relevantes para o dashboard sao refletidas no UPDATE de provas_digitais.
--
-- Pre-condicao: publicacao supabase_realtime ja existe (criada pelo Supabase).
-- Idempotente: ADD TABLE com IF NOT EXISTS nao e suportado nativamente,
-- mas se a tabela ja estiver na publicacao, o Postgres levanta um erro.
-- Para idempotencia, usamos bloco DO.
--
-- Aplicacao: executar via SQL Editor do Supabase Dashboard ou via MCP
-- execute_sql. NAO usar Alembic (publicacoes sao infra Supabase, nao dominio).
-- =============================================================================

DO $$
BEGIN
  -- Verifica se provas_digitais ja esta na publicacao
  IF NOT EXISTS (
    SELECT 1
    FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime'
      AND schemaname = 'public'
      AND tablename = 'provas_digitais'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.provas_digitais;
    RAISE NOTICE 'provas_digitais adicionada a publicacao supabase_realtime';
  ELSE
    RAISE NOTICE 'provas_digitais ja esta na publicacao supabase_realtime (skip)';
  END IF;
END
$$;
