# Contributing to DRAX AI

Thank you for your interest in contributing to DRAX AI!

## Development Guidelines

1. **Architecture First**: Always register new capabilities as structured `Tool` definitions under `backend/tools/` using the `@register_tool` decorator.
2. **Offline-First & Free**: Base core capabilities (wake word, speech recognition, tasks, reminders, media controls, apps) must not depend on paid external APIs.
3. **Safety & Permissions**: Dangerous actions (system power, financial transfers, file deletion) must set `requires_confirmation = True` and appropriate `risk_level`.
4. **Testing**: Write unit tests under `tests/` for any new planner rules or tools.

## Running Tests

```bash
.\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, '.'); import tests.test_wake_word; import tests.test_app_matching; import tests.test_planner; import tests.test_db_features; import tests.test_safety; print('Tests pass!')"
```
