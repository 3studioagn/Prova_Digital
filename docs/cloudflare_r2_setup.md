# Configuracao do Cloudflare R2 — Passos Manuais

O bucket `rastreio-provas-artes` ja foi criado via MCP. Os passos abaixo
precisam ser feitos no dashboard da Cloudflare.

## 1. Configurar CORS

Acesse: **Cloudflare Dashboard > R2 > rastreio-provas-artes > Settings > CORS Policy**

Cole a seguinte configuracao JSON:

```json
[
  {
    "AllowedOrigins": ["http://localhost:3000"],
    "AllowedMethods": ["GET", "PUT"],
    "AllowedHeaders": ["Content-Type", "Authorization"],
    "MaxAgeSeconds": 3600
  }
]
```

> **Nota:** Em producao, substituir `http://localhost:3000` pelo dominio real
> do frontend. Adicionar como novo item no array, mantendo o localhost para dev.

## 2. Criar API Token com escopo minimo

Acesse: **Cloudflare Dashboard > R2 > Overview > Manage R2 API Tokens > Create API Token**

Configuracao:
- **Token name:** `rastreio-provas-backend`
- **Permissions:** Object Read & Write
- **Specify bucket(s):** Apply to specific buckets only > `rastreio-provas-artes`
- **TTL:** opcional (sem expiracao para dev, com expiracao para prod)

Apos criar, copie os valores para o `.env`:

```
R2_ACCESS_KEY_ID=<Access Key ID gerado>
R2_SECRET_ACCESS_KEY=<Secret Access Key gerado>
R2_ENDPOINT_URL=https://20ab724c91f6bda669eecfe7c51c9171.r2.cloudflarestorage.com
R2_BUCKET_NAME=rastreio-provas-artes
R2_ACCOUNT_ID=20ab724c91f6bda669eecfe7c51c9171
```

## 3. Validar conectividade

Apos configurar o `.env`, execute o smoke test:

```bash
cd rastreio-provas-digitais
python scripts/smoke_r2.py
```

O script faz upload, listagem, download e exclusao de um arquivo de teste.
Todos os 4 passos devem retornar OK.
