PRD: FitTrack AI - Product Requirements Document
1. Overview
FitTrack AI is a distributed information system designed for health and fitness management. It integrates cloud-based services, generative AI, and a modern desktop interface.

2. Architecture & Tech Stack
UI: Desktop application using PySide6 (Microfrontends - MVP pattern).

Backend: FastAPI organized with CQRS/MVC patterns.

Database: Cloud-based SQL Server (via somee.com) using Event Sourcing approach.

AI Integration: Ollama RAG container running in Docker for nutritional and fitness consultation.

Gateway: External services accessed via Gateway pattern.

3. Functional Requirements
User Management: Authentication and profile management.

Data Operations: * Search and display of nutrition/workout data.

Real-time visualization using QtCharts.

Data entry (meals, weights, workouts).

AI Consultant: RAG-based agent for personalized health advice.

4. Development Methodology
Developed using PIV (Process, Iteration, Validation) methodology.

Managed via GitHub with code agent-assisted design.