# Ollama in Docker

FitTrackAI uses the official Ollama image and the persistent Docker volume
`fittrackai-ollama-data`. The volume is shared with the previously validated
manual runtime, so existing models are reused.

## Start

If the legacy container is still using port `11434`, stop it without deleting
its model volume:

```powershell
docker stop fittrackai-ollama-runtime
```

Start the repository-managed service:

```powershell
docker compose up -d ollama
```

Check the service and installed models:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
docker compose exec ollama ollama list
```

## Required models

Pull a model only when it is absent from `ollama list`:

```powershell
docker compose exec ollama ollama pull aminadaven/dictalm2.0-instruct:q4_k_m
docker compose exec ollama ollama pull llava
```

Stop the service while retaining all downloaded models:

```powershell
docker compose down
```

Do not use `docker compose down -v`; that command deletes the persistent model
volume.
