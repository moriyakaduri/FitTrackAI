# FitTrackAI Product Requirements Document

## 1. Product goal

FitTrackAI is a Hebrew right-to-left desktop application for personal nutrition
and fitness tracking. It combines daily data entry, cloud persistence,
visual dashboards, database-backed retrieval, barcode product lookup, and
local generative AI.

The submission demonstrates a complete desktop-to-API flow rather than a
production medical platform. AI nutrition values are estimates and remain
editable before a user saves them. External barcode results also populate the
form only; saving a meal is always an explicit user action.

## 2. Intended users

- Students or adults who want a simple daily meal, weight, and workout diary.
- Users who prefer a Hebrew desktop interface.
- Users who want locally hosted AI assistance without sending prompts to a
  commercial language-model API.
- A project team that shares persisted data and uploaded images through cloud
  services while developing the desktop client independently.

## 3. Functional requirements

### Authentication and navigation

- Authenticate an existing user through the FastAPI backend.
- Move between login, dashboard, AI advisor, data entry, trends, and motivation
  feature views.
- Preserve the logged-in username in the presenter for subsequent operations.

### Tracking and retrieval

- Search nutrition facts and article summaries stored in SQL Server.
- Look up a packaged product by barcode through OpenFoodFacts and populate the
  meal form. The lookup must not write to the database.
- Record meals, body weight, and workouts.
- Store activity as append-only `UserEvents`.
- Retrieve meal details by event identifier.
- Project events into daily meals, workouts, calorie/protein totals, weight
  history, and dashboard charts.

### AI advisor and RAG

- Send Hebrew questions through FastAPI to DictaLM running in Ollama.
- Retrieve relevant nutrition facts and article summaries from the database.
- Include retrieved context and the user's remaining daily calories in the
  model prompt.
- Return a readable Hebrew response and expose connection failures clearly.

### Food image analysis

- Accept a local food image from the data-entry window.
- Upload the original image to Cloudinary and return its HTTPS `secure_url`.
- Compress a copy locally for AI inference.
- Use LLaVA to identify the food and estimate nutrition.
- Use DictaLM to produce structured Hebrew fields.
- Reject unreliable or zero-calorie model results instead of presenting them
  as successful meals.
- Populate editable meal fields; saving remains a separate user action.

### Image chat

- Accept a local food image together with the user's typed question from the
  AI advisor.
- Upload the original image to Cloudinary and return its HTTPS `secure_url`.
- Use LLaVA to inspect the image in light of that question.
- Include relevant database/RAG context in the follow-up prompt.
- Use DictaLM to produce a Hebrew answer about the image and the question.
- Image chat is a question-answering flow, not a duplicate of structured
  meal-field extraction.

### Visualization

- Display a meals table and meal detail dialog.
- Display macro composition, calorie-target, and weight-history charts using
  QtCharts.
- Display workout duration and weight trend summaries.

## 4. Architecture and technology

- **Desktop:** Python 3.10 and PySide6.
- **Desktop composition:** feature-sliced `QWidget` modules for authentication,
  AI advisor, data entry, trends, and motivation, composed by
  `FitTrackApplication`.
- **MVP:** `FitTrackPresenter` coordinates primary view actions and the HTTP
  API. Login and meal saving use presenter-owned background workers so the GUI
  does not freeze. Workers are execution helpers, not a replacement for the
  presenter. Dedicated AI workers call `/ai/*` directly because inference is
  long-running. Weight and workout saves currently call the presenter
  synchronously.
- **Backend:** FastAPI with separate command and query route modules.
- **CQRS interpretation:** `/commands/*` routes append activity; `/queries/*`
  routes read projections, local search, and barcode lookup. Both sides
  intentionally share one database and ORM model set. No command bus or second
  database is claimed.
- **Event Sourcing interpretation:** meals, weights, and workouts use an
  append-only user activity event log. Users, articles, and nutrition facts
  remain conventional relational tables.
- **Database:** cloud-hosted Microsoft SQL Server on Somee, accessed with
  SQLAlchemy and `pyodbc`.
- **Gateway:** `backend.gateway.ExternalServicesGateway` is the single boundary
  for Ollama, Cloudinary, and OpenFoodFacts.
- **AI runtime:** official Ollama Docker image with persistent model storage.
  Compose requests NVIDIA GPU access when the host provides it. CPU execution
  remains valid and is slower.
- **Models:** `aminadaven/dictalm2.0-instruct:q4_k_m` and `llava`.
- **Cloud media:** Cloudinary uploads configured only by environment variables.
- **External nutrition:** OpenFoodFacts barcode lookup from Data Entry.

Detailed diagrams and pattern evidence are in
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## 5. Desktop microfrontend interpretation

The project uses a desktop-appropriate interpretation of microfrontends:
independently organized feature-view modules with a stable composition shell.
These modules are not separately deployed web applications. Each feature owns
real UI behavior and workers; `gui_main.py` composes them into one PySide6
process. This provides visible ownership boundaries without introducing a
plugin framework or distributed web architecture that the product does not
need.

## 6. External configuration

Runtime configuration is supplied through environment variables. No valid
credential belongs in source control.

- SQL Server connection variables configure database access.
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and
  `CLOUDINARY_API_SECRET` configure image upload.
- `OLLAMA_URL`, `OLLAMA_TEXT_MODEL`, `OLLAMA_VISION_MODEL`, and optional
  generation limits configure local AI.

## 7. Quality and operational requirements

- Long API and AI calls that would freeze the GUI run outside the Qt UI thread.
- Model, barcode, and provider failures return explicit error states.
- Docker model storage survives container replacement.
- GPU offload is best-effort and may be partial, depending on host VRAM.
- The GUI remains usable when optional satellite windows are opened or closed.
- Database write tests use identifiable append-only records and never delete
  existing user data.
- Secrets and generated Python bytecode must not be committed.

## 8. Validation and acceptance

The product is accepted for submission when:

- FastAPI and the PySide6 shell start on Python 3.10.
- Login, search, barcode lookup, details, dashboard queries, and navigation
  work.
- Meal, weight, and workout commands each append one event and appear in the
  dashboard projection.
- DictaLM returns a real Hebrew advisor response with database context.
- Data-entry image analysis returns structured Hebrew meal fields.
- Image chat answers two different questions about the same image differently.
- Both image endpoints return fetchable Cloudinary HTTPS URLs.
- A known barcode returns real OpenFoodFacts product data without auto-save.
- Ollama starts from the repository Compose configuration and lists both
  required models.

The real investigation and validation history is recorded in
[`PIV.md`](PIV.md).
