# FitTrackAI Product Requirements Document

## 1. Product goal

FitTrackAI is a Hebrew right-to-left desktop application for personal nutrition
and fitness tracking. It combines daily data entry, cloud persistence,
visual dashboards, database-backed retrieval, and local generative AI.

The submission demonstrates a complete desktop-to-API flow rather than a
production medical platform. AI nutrition values are estimates and remain
editable before a user saves them.

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

- Accept a local food image from the desktop client.
- Upload the original image to Cloudinary and return its HTTPS `secure_url`.
- Compress a copy locally for AI inference.
- Use LLaVA to identify the food and estimate nutrition.
- Use DictaLM to produce structured Hebrew fields.
- Reject unreliable or zero-calorie model results instead of presenting them
  as successful meals.
- Populate editable meal fields; saving remains a separate user action.
- Support the same structured result in the AI chat image flow.

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
  API. AI workers call dedicated AI endpoints directly to keep long inference
  off the UI thread.
- **Backend:** FastAPI with separate command and query route modules.
- **CQRS interpretation:** `/commands/*` routes append activity; `/queries/*`
  routes read and build projections. Both sides intentionally share one
  database and ORM model set.
- **Event Sourcing interpretation:** meals, weights, and workouts use an
  append-only user activity event log. Reference tables such as users,
  articles, and nutrition facts use conventional relational persistence.
- **Database:** cloud-hosted Microsoft SQL Server through SQLAlchemy and ODBC.
- **Gateway:** `backend.gateway.ExternalServicesGateway` is the single boundary
  for Ollama, Cloudinary, and optional OpenFoodFacts access.
- **AI runtime:** official Ollama Docker image with persistent model storage.
- **Models:** `aminadaven/dictalm2.0-instruct:q4_k_m` and `llava`.
- **Cloud media:** Cloudinary uploads configured only by environment variables.

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

- Long API and AI calls run outside the Qt UI thread.
- Model and provider failures return explicit error states.
- Docker model storage survives container replacement.
- The GUI remains usable when optional satellite windows are opened or closed.
- Database write tests use identifiable append-only records and never delete
  existing user data.
- Secrets and generated Python bytecode must not be committed.

## 8. Validation and acceptance

The product is accepted for submission when:

- FastAPI and the PySide6 shell start on Python 3.10.
- Login, search, details, dashboard queries, and navigation work.
- Meal, weight, and workout commands each append one event and appear in the
  dashboard projection.
- DictaLM returns a real Hebrew advisor response with database context.
- LLaVA returns structured Hebrew food analysis through both image endpoints.
- Both image endpoints return fetchable Cloudinary HTTPS URLs.
- Ollama starts from the repository Compose configuration and lists both
  required models.

The real investigation and validation history is recorded in
[`PIV.md`](PIV.md).
