-- =============================================================================
-- RLS 001: Habilitar Row Level Security em todas as tabelas de dominio
-- =============================================================================
-- IMPORTANTE: Este script e idempotente — pode ser reaplicado sem efeitos colaterais.
--
-- Por que habilitar RLS?
--   O Supabase expõe o PostgreSQL via API REST (PostgREST). Sem RLS, qualquer
--   usuario autenticado com a anon key poderia ler/escrever qualquer registro.
--   Com RLS habilitado, o acesso padrao e NEGADO — so passa o que as policies
--   explicitamente permitem.
--
-- Nota: habilitar RLS sem criar policies significa que NINGUEM consegue acessar
-- os dados via API do Supabase (PostgREST). O acesso via service_role_key
-- (usado pelo backend FastAPI) ignora RLS, entao o backend continua funcionando.
-- As policies serao adicionadas incrementalmente nas proximas waves.
-- =============================================================================

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE provas_digitais ENABLE ROW LEVEL SECURITY;
ALTER TABLE movimentacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE etiquetas ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE configuracoes_sistema ENABLE ROW LEVEL SECURITY;
