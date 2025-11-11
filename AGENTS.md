# Agent Playbook & Ownership Matrix

This document assigns ownership of each major area in the repo to a virtual
agent. When working in Cursor, use `@<agent>` in your prompts to get targeted
assistance.

| Path / Responsibility | Agent | Purpose |
| --- | --- | --- |
| `src/1_shared_domain/` (entities, business rules) | `@domain-guru` | Define domain models, validations and ubiquitous language. |
| `src/2_shared_application/` (DTOs, interfaces) | `@application-architect` | Design service contracts, DTO schemas and inter-module APIs. |
| `src/apps/3_backend/` (API + persistence) | `@backend-conductor` | Implement application services, adapters, controllers and database integration. |
| `src/apps/4_trainer/` (fine-tuning pipelines) | `@trainer-maestro` | Manage training jobs, GPU orchestration and experiment tracking. |
| `src/apps/5_web_frontend/` (Reflex UI) | `@frontend-visionary` | Build Reflex components, pages and API clients. |
| `security/` (cryptographic utilities) | `@security-sentinel` | Maintain encryption helpers, secret storage and key-rotation flows. |
| `infrastructure/` (deployment scripts) | `@ops-pilot` | Provision infrastructure, automate deployments and manage environments. |

Use this matrix as the single source of truth when routing tasks in Cursor.

