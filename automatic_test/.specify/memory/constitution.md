# Automatic Test Constitution

## Core Principles

### I. Library-First

Every feature starts as a standalone library. Libraries must be:

- Self-contained and independently testable
- Documented with a clear, single purpose
- No "organizational-only" libraries — every library must do something

### II. CLI Interface

Every library exposes functionality via CLI:

- Text in/out protocol: stdin/args → stdout, errors → stderr
- Support both JSON and human-readable formats
- No library is "internal only" without documented justification

### III. Test-First (NON-NEGOTIABLE)

TDD is mandatory:

- Tests written → User approved → Tests fail → Then implement
- Red-Green-Refactor cycle strictly enforced
- No implementation merges without prior failing test

### IV. Integration Testing

Required for:

- New library contract tests
- Contract changes between libraries
- Inter-service communication
- Shared schemas

### V. Simplicity

Start simple, apply YAGNI principles:

- Complexity must be justified
- Three similar lines before any abstraction
- No speculative generality
- Require minimum viable complexity: if a simpler approach works, adopt it first
- Prioritize intent-driven development: every line of code should trace back to a user or business intent.

### VI. Develop Princople
- Use SOLID principal
- Use KISS principal
- Use Python 3.11+
- Use Service to wrap common operations
- Use Repository to wrap common EF Core queries (CRUD)
- Use Typescript with Vue


## Additional Constraints

- All libraries versioned with MAJOR.MINOR.BUILD
- Breaking changes require MAJOR bump and migration guide
- Structured logging required in all services

## Development Workflow

- PRs must include Constitution Check section
- All complexity violations documented in Complexity Tracking table
- Amendments require documentation + approval + migration plan


## Governance

This constitution supersedes all other practices.
Amendments require: documentation, approval, and migration plan.
All PRs/reviews must verify compliance.
All response must use the Traditional Chinese

**Version**: 1.0.0 | **Ratified**: 2026-05-10 | **Last Amended**: 2026-05-10
