# Infra cheatsheet

## Start the dev stack (Postgres + Redis)
```bash
docker compose -f infra/docker-compose.dev.yml up -d
```

## Run migrations against the dev Postgres
```bash
cd backend && alembic upgrade head
```

## Start vLLM on the host (recommended — needs your GPU)
```bash
vllm serve Qwen/Qwen2.5-0.5B-Instruct \
  --max-model-len 8192 \
  --port 8000
```
The OpenAI-compatible endpoint will then be reachable at `http://localhost:8000/v1`.
xgrammar is vLLM's default structured-outputs backend now, so no flag is needed
(the old `--guided-decoding-backend` was removed in vLLM 0.21). On a host without
the CUDA toolkit (`nvcc`), add `--enforce-eager` and set
`VLLM_USE_FLASHINFER_SAMPLER=0` to avoid JIT compilation.

## Run the ephemeral test Postgres (port 55432)
```bash
docker compose -f infra/docker-compose.test.yml up -d
```

## Wipe everything (containers + named volume)
```bash
docker compose -f infra/docker-compose.dev.yml down -v
docker compose -f infra/docker-compose.test.yml down -v
```
