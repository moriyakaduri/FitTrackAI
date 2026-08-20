# FitTrackAI Architecture

This document describes the implemented project, including deliberate
lightweight interpretations used for a university desktop application.

## Overall system

```mermaid
flowchart LR
    subgraph Desktop["PySide6 desktop"]
        Shell["FitTrackApplication\ncomposition shell"]
        Views["Feature views\nauth · dashboard · data entry\nAI advisor · trends"]
        Presenter["FitTrackPresenter\nMVP presenter"]
        Shell --> Views
        Views --> Presenter
    end

    Presenter -->|HTTP JSON| API["FastAPI\nbackend.main"]
    Views -->|long-running AI workers| API

    API --> Commands["commands.py\nwrite side"]
    API --> Queries["queries.py\nread side"]
    API --> Gateway["ExternalServicesGateway"]

    Commands --> DB[("Cloud SQL Server")]
    Queries --> DB
    API --> DB
    Gateway --> Ollama["Ollama in Docker\nDictaLM + LLaVA"]
    Gateway --> Cloudinary["Cloudinary\nimage storage"]
```

`backend/main.py` is the FastAPI composition root. It registers routers,
orchestrates database context for AI prompts, and delegates external calls to
the canonical Gateway.

## Desktop feature modules and MVP

```mermaid
flowchart TD
    Shell["gui_main.py\nFitTrackApplication"]
    Dashboard["gui_main.py\nDashboardView"]
    Presenter["presenter.py\nFitTrackPresenter"]

    Shell --> Auth["features/auth_view.py"]
    Shell --> Dashboard
    Shell --> AI["features/ai_advisor_view.py"]
    Shell --> Entry["features/data_entry_view.py"]
    Shell --> Trends["features/trends_view.py"]
    Shell --> Motivation["features/motivation_view.py"]

    Auth --> Presenter
    Dashboard --> Presenter
    Entry --> Presenter
    Trends --> Presenter
    AI -->|dedicated HTTP workers| API["FastAPI AI endpoints"]
```

The desktop interpretation of microfrontends is feature-sliced ownership:
each module contains a real `QWidget` feature and its workers, while one shell
composes them into a single process. It is intentionally not a separately
deployed web-microfrontend system.

MVP is applied pragmatically:

- **View:** feature widgets and `DashboardView`.
- **Presenter:** `FitTrackPresenter`, which coordinates primary user actions
  and API requests.
- **Model:** backend JSON projections and SQLAlchemy entities accessed through
  the API.
- AI workers call `/ai/*` directly to avoid blocking the GUI and are documented
  as a deliberate presenter bypass.

## CQRS request split

```mermaid
flowchart LR
    UI["PySide6 action"] --> Choice{Operation}

    Choice -->|write| CommandAPI["POST /commands/*"]
    CommandAPI --> Meal["log-meal"]
    CommandAPI --> Weight["log-weight"]
    CommandAPI --> Workout["log-workout"]
    Meal --> Append["append_user_event"]
    Weight --> Append
    Workout --> Append
    Append --> Events[("UserEvents")]

    Choice -->|read| QueryAPI["GET /queries/*"]
    QueryAPI --> Summary["nutrition-summary"]
    QueryAPI --> Details["meal-details"]
    QueryAPI --> Search["search"]
    Summary --> Projection["get_nutrition_summary"]
    Projection --> Events
    Details --> Events
    Search --> Reference[("NutritionFacts / Articles")]
```

This is a CQRS-inspired HTTP boundary. Commands and queries have different
routes and responsibilities but intentionally share the same SQL Server and
SQLAlchemy models; no command bus or second database is claimed.

## User activity event log and projection

```mermaid
sequenceDiagram
    participant User
    participant View as PySide6 feature view
    participant Presenter as FitTrackPresenter
    participant Command as FastAPI command route
    participant Store as UserEvents
    participant Query as nutrition-summary
    participant Dashboard

    User->>View: Save meal, weight, or workout
    View->>Presenter: Submit action
    Presenter->>Command: POST /commands/log-*
    Command->>Store: INSERT immutable activity event
    Command-->>Presenter: success
    Presenter->>Query: GET projection
    Query->>Store: Read user's events
    Query->>Query: Fold daily totals, history, lists
    Query-->>Dashboard: Dashboard JSON
```

Event Sourcing is limited to user activity. Command handlers append events and
do not update earlier events; `get_nutrition_summary` folds the log into a read
projection. Users, nutrition facts, and articles remain normal relational
tables. Production features such as snapshots and schema upcasting are outside
the course-scale scope.

## AI advisor and RAG

```mermaid
sequenceDiagram
    participant User
    participant AIView as AI advisor view
    participant API as /ai/analyze-food
    participant DB as SQL Server
    participant Gateway
    participant DictaLM as DictaLM in Ollama

    User->>AIView: Hebrew nutrition question
    AIView->>API: message + username
    API->>DB: Nutrition summary
    API->>DB: Match NutritionFacts and Articles
    DB-->>API: User totals + relevant context
    API->>Gateway: Grounded Hebrew prompt
    Gateway->>DictaLM: Ollama generate request
    DictaLM-->>Gateway: Hebrew answer
    Gateway-->>API: Formatted response
    API-->>AIView: Hebrew response
```

The RAG implementation uses deterministic SQL keyword retrieval rather than a
vector database. It is appropriate for the small existing corpus and has been
validated with known nutrition and article records.

## Food image and Cloudinary flow

```mermaid
flowchart LR
    Image["User-selected food image"] --> Endpoint["/ai/analyze-image\nor /ai/chat-image"]
    Endpoint --> Upload["Gateway upload"]
    Upload --> Cloudinary["Cloudinary"]
    Cloudinary --> URL["HTTPS secure_url"]

    Endpoint --> Compress["Local resize + JPEG compression"]
    Compress --> LLaVA["LLaVA via Ollama"]
    LLaVA --> English["Structured English JSON"]
    English --> DictaLM["DictaLM translation"]
    DictaLM --> Validate["Parse + validate Hebrew name/macros"]
    Validate --> Response["GUI-compatible response"]
    URL --> Response
    Response --> Edit["Editable meal fields / chat bubble"]
    Edit --> Save{"User chooses to save?"}
    Save -->|yes| Command["Meal command"]
    Save -->|no| End["No database write"]
```

The original image is uploaded without paid transformations. A compressed copy
is generated locally for model inference. A successful response includes the
Cloudinary `secure_url`; model failures cannot masquerade as successful
zero-valued meals.

## Gateway boundary

`backend/gateway.py` owns:

- Cloudinary configuration and upload;
- Ollama text and vision calls;
- AI response parsing and structured nutrition validation;
- optional OpenFoodFacts lookup.

FastAPI routes do not contain provider-specific HTTP calls. OpenFoodFacts is
implemented but is not part of a current user-facing flow, so it must not be
presented as a validated feature.

## Deployment boundaries

- PySide6 and FastAPI run as separate local Python processes.
- SQL Server and Cloudinary are remote services.
- Ollama runs locally in the official Docker image on port 11434.
- Model files are stored in the named Docker volume
  `fittrackai-ollama-data`.
- Secrets are supplied at runtime through environment variables.
