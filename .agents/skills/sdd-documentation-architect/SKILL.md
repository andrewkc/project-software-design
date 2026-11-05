---
name: sdd-documentation-architect
description: Create and maintain source-grounded, versioned software documentation using iterative Spec-Driven Development for the bodega-management project.
---
# SDD Documentation Architect

Read `AGENTS.md`, the governance constitution, product scope, relevant use case, business rules, entities and open questions before editing.

## Source discipline
Classify statements as Confirmed, Derived, Proposed or Pending. Never invent stack, architecture, database schema, hosting, security targets, performance targets, AI algorithm or forecast method.

## Workflow
1. Discover the user/business problem and evidence.
2. Specify behavior, permissions, rules, exceptions and acceptance criteria.
3. Review ambiguity and traceability with the team.
4. Plan technical approach only after decisions are made.
5. Break work into verifiable tasks.
6. Implement only when requested and specification is reviewed.
7. Validate with tests and record results.
8. Update docs and decisions from discoveries.

## Feature checklist
Identifier/status; goal/scope; actors/permissions; preconditions/postconditions; main/alternate/exception flows; business rules; entities/data; acceptance criteria; test scenarios; dependencies; open questions; traceability.

Preserve identifiers CU/EN/RN/AN/TN. Check stock behavior against RN-03…RN-06, promotions against RN-07/RN-09 and AI boundaries against RN-08. Do not implement when the request is documentation-only.
