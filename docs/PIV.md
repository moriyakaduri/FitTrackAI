# FitTrackAI PIV Evidence

PIV is used here as **Problem → Investigation → Change → Validation**. This
record describes work that was actually performed on the
`runtime-validation` branch; it does not invent earlier project history.

## Iteration 1 — Existing project baseline

**Problem:** Establish a safe baseline before changing a shared university
project.

**Investigation:** The repository and remote state were checked, the existing
PySide6/FastAPI structure was mapped, and commit `a016008` was retained as the
baseline.

**Change:** No source change. Work continued on `runtime-validation`, not
`main`.

**Validation/result:** The branch started clean and existing history remained
available for comparison.

## Iteration 2 — Static current-state audit

**Problem:** The short PRD claimed Docker, microfrontends, RAG, CQRS, Event
Sourcing, and Gateway behavior without enough implementation evidence.

**Investigation:** Source files, imports, routes, models, event flow, AI calls,
dependencies, generated files, and documentation were inspected read-only.

**Change:** No application code was changed. A current-state audit was
produced for planning.

**Validation/result:** Working-shaped features and unsupported claims were
separated. Runtime validation became the next gate.

## Iteration 3 — Runtime and dependency repair

**Problem:** Static inspection could not prove that FastAPI, PySide6, SQL
Server, multipart upload, Docker, or Ollama worked on the target Windows
machine.

**Investigation:** A Python 3.10 virtual environment was used. FastAPI import
showed a missing `python-multipart` dependency. Backend, API documentation,
database access, and the desktop shell were started independently.

**Change:** The missing package was installed in the isolated environment.
No broad refactor was performed.

**Validation/result:** FastAPI returned HTTP 200, Swagger/OpenAPI loaded, the
cloud database responded, and the PySide6 login shell rendered.

## Iteration 4 — Ollama Docker and model validation

**Problem:** The application required local DictaLM and LLaVA models, but their
runtime availability was unknown.

**Investigation:** Ollama was run in the official Docker image on port 11434
with named volume `fittrackai-ollama-data`. Installed models and direct
generation were tested.

**Change:** DictaLM Q8 and LLaVA were downloaded to persistent storage. The Q8
model proved impractical under available memory, so the official Q4_K_M
quantization was evaluated.

**Validation/result:** LLaVA completed direct image inference. DictaLM
Q4_K_M returned Hebrew in about 100 seconds cold and about 29 seconds warm.
The repository Compose artifact was then prepared to reuse the same volume.

## Iteration 5 — AI advisor and basic RAG

**Problem:** The Q8 advisor timed out and the database context needed
end-to-end proof.

**Investigation:** Direct generation and `/ai/analyze-food` were measured.
Known database records were selected for deterministic nutrition and article
questions.

**Change:** Commit `e0b6135` changed the default text model to
`aminadaven/dictalm2.0-instruct:q4_k_m` and added configurable context/output
limits.

**Validation/result:** The advisor returned genuine Hebrew without a hidden
connection error. A banana question reproduced 89 kcal and 1.1 g protein from
`NutritionFacts`; a training question reproduced the article guidance of
1.6–2.2 g protein/kg and identified RAG context.

## Iteration 6 — Food image AI

**Problem:** `/ai/analyze-image` could turn model failures into successful
zero-valued meals. `/ai/chat-image` took about 991 seconds and misidentified a
banana as salad.

**Investigation:** A safe banana image was sent through both endpoints. The
chat path was found to duplicate vision and free-form translation instead of
using the stricter structured analyzer.

**Change:** Commit `542a7cb` added numeric/name validation, explicit failure
semantics, full macro fields, and one shared structured image-analysis path.

**Validation/result:** Both endpoints identified the banana in Hebrew with
105 kcal, 1 g protein, 0 g fat, and 27 g carbohydrates. Responses completed in
about 143–147 seconds. A forced model failure raised a clear error rather than
returning zero nutrition as success.

## Iteration 7 — Cloudinary

**Problem:** Upload errors were swallowed and the returned `secure_url` was
discarded.

**Investigation:** Cloudinary configuration scopes were checked without
displaying values. A 4.3 KB local test image was used to minimize storage and
network usage.

**Change:** Commit `d7f0b21` removed placeholder credentials, required
environment configuration, surfaced provider errors, and returned
`secure_url` from both image endpoints.

**Validation/result:** Two real uploads succeeded in `fittrack_food` and
`fittrack_chat`. Both HTTPS URLs used `res.cloudinary.com` and returned image
content when fetched. No transformations or paid features were used.

## Iteration 8 — Controlled data persistence

**Problem:** API success alone did not prove that all event types persisted
and appeared in projections.

**Investigation:** Event counts were captured before and after one controlled
meal, weight, and workout command for an existing test user.

**Change:** No code change was required.

**Validation/result:** The following events were appended and projected:

- Meal event `10458`: `FASTSUB_20260820_154753_MEAL`, 321 kcal, 17 g protein.
- Weight event `10459`: 73.218 kg on 2026-08-20.
- Workout event `10460`: `FASTSUB_20260820_154753_WORKOUT`, 19 minutes and
  152 kcal.

Each type increased by exactly one; meal details also matched the stored row.

## Iteration 9 — Modular desktop feature views

**Problem:** All UI features lived in one large `gui_main.py`, making the PRD's
desktop microfrontend claim indefensible.

**Investigation:** Class dependencies and presenter coupling were mapped. A
web-style distributed architecture was rejected as inappropriate and risky.

**Change:** Commit `aa98161` extracted real authentication, AI advisor,
data-entry, trends, motivation, and shared UI implementations into the
`features` package. `FitTrackApplication` remained the composition shell and
the presenter contract stayed stable.

**Validation/result:** Offscreen regression instantiated all three stacked
pages and all five modular feature windows. The login video path and explicit
data-entry API configuration remained valid.

## Iteration 10 — Architecture clarification

**Problem:** The active Gateway was duplicated in `backend/main.py`, while
`backend/gateway.py` contained stale model names and behavior.

**Investigation:** MVP, CQRS, event-log, and external-service flows were traced
to exact classes and routes.

**Change:** Commit `536aa73` made `backend/gateway.py` canonical, reduced
`backend/main.py` to orchestration, removed dead CQRS imports, labeled the
append/fold roles, and removed an import-time dependency on the FastAPI app
from the article utility.

**Validation/result:** FastAPI generated all 11 OpenAPI paths, the canonical
Gateway identity was verified, SQL dashboard projection returned HTTP 200,
and known Hebrew nutrition search still passed.

## Cursor/code-agent workflow evidence

Cursor's code agent supported the project as an engineering tool:

- repository search and read-only architecture mapping before edits;
- isolated branch and checkpoint commits for each meaningful change;
- terminal-driven FastAPI, Docker, API, database, and PySide6 validation;
- small targeted patches instead of broad rewrites;
- explicit inspection of staged diffs before commits;
- credential-presence checks that never printed secret values;
- failure reproduction before fixes and regression after fixes.

The team remains responsible for requirements, credentials, final review,
Cloudinary/Docker accounts, and submission decisions. Agent output is evidence
of the development process, not a substitute for team understanding.
