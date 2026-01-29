# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting significant architectural choices made in this project.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision along with its context and consequences. ADRs help:

- **Future developers** understand why decisions were made
- **Current team** remember trade-offs and alternatives
- **Code reviewers** evaluate changes against architectural principles
- **New team members** onboard faster

## ADR Format

Each ADR follows the template in [template.md](template.md) with these sections:

- **Status**: Proposed, Accepted, Deprecated, or Superseded
- **Context**: Problem being solved and forces at play
- **Decision**: The chosen solution
- **Consequences**: Positive, negative, and neutral impacts
- **Alternatives Considered**: What other options were evaluated
- **References**: Links to documentation, code, and research
- **Notes**: Additional context and future considerations

## Current ADRs

| Number | Title | Status | Date |
|--------|-------|--------|------|
| [0001](0001-repository-command-pattern.md) | Use Repository + Command Pattern for Business Logic | Accepted | 2025-01-29 |
| [0002](0002-decorator-based-rbac.md) | Use Decorator-Based RBAC with Co-Located Permissions | Accepted | 2025-01-29 |
| [0003](0003-correlation-id-vs-opentelemetry.md) | Use Correlation IDs for Distributed Tracing (Not OpenTelemetry) | Accepted | 2025-01-29 |
| [0004](0004-two-tier-caching.md) | Use Two-Tier Memory + Redis Caching for Hot Keys | Accepted | 2025-01-29 |

## Creating a New ADR

1. Copy the [template.md](template.md)
2. Name it `XXXX-title-in-kebab-case.md` where XXXX is the next sequential number
3. Fill in all sections with specific details
4. Update this README with the new ADR
5. Submit for review

## ADR Lifecycle

- **Proposed**: Under discussion, not yet implemented
- **Accepted**: Decision made and implemented
- **Deprecated**: No longer recommended but still in codebase
- **Superseded**: Replaced by a newer ADR (link to replacement)

## When to Write an ADR

Write an ADR when making decisions that:

- Affect system architecture or design patterns
- Have significant trade-offs or alternatives
- Will impact future development
- Require team consensus
- Solve recurring problems
- Establish standards or conventions

Examples:
- Choosing between patterns (Repository vs Service Layer)
- Selecting technologies (OpenTelemetry vs Correlation IDs)
- Defining system boundaries (Monolith vs Microservices)
- Establishing conventions (RBAC patterns, caching strategies)

## When NOT to Write an ADR

Skip ADRs for:

- Implementation details (how to write a function)
- Obvious choices (using FastAPI in a FastAPI project)
- Temporary decisions (quick fixes, experiments)
- Minor refactoring
- Bug fixes

## Resources

- [Michael Nygard's ADR format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) - Original ADR format
- [adr.github.io](https://adr.github.io/) - ADR community resources
- [ADR Tools](https://github.com/npryce/adr-tools) - Command-line tools for managing ADRs

## Related Documentation

- [docs_site/architecture/](../../docs_site/architecture/) - Detailed architecture documentation
- [CLAUDE.md](../../CLAUDE.md) - Development guidelines for AI agents
- [docs_site/guides/](../../docs_site/guides/) - Implementation guides
