# FoodPharmer Challenge — Agent Instructions

## Project

This repository contains the FoodPharmer Challenge MVP.

The application analyzes marketing claims made on packaged food products and compares those claims against supplied FSSAI regulations.

The application is NOT intended to determine whether a food is healthy or unhealthy.

## Core principle

The product evaluates:

> "Is this marketing claim supported by the applicable FSSAI criteria?"

It does NOT evaluate:

> "Is this food healthy?"

Do not introduce subjective health scores or nutritional-quality judgments.

## Current MVP

V1 pipeline:

Package image
→ extract marketing claims and relevant nutrition information
→ compare claims against supplied FSSAI rules
→ produce structured claim-level verdicts and applicable regulatory classifications
→ calculate deterministic Marketing Gap Score

## Claim verdicts

Every claim must receive exactly one of:

- SUPPORTED
- NOT_SUPPORTED
- INSUFFICIENT_INFORMATION

Never guess when the supplied image does not contain enough information.

## Regulatory source

FSSAI regulations supplied by the application are the source of truth for claim evaluation.

Do not rely on the model's general knowledge of FSSAI regulations when evaluating a claim.

Do not invent regulatory thresholds.

If the supplied regulations do not contain enough information to evaluate a claim, return INSUFFICIENT_INFORMATION.

## Regulatory classifications

The response may separately report a regulatory classification (for example,
"high in sugar") only when the supplied FSSAI rules explicitly define that
classification and the visible package information is sufficient to apply its
criteria.

Regulatory classifications are factual rule applications, not health scores or
health recommendations. They do not affect the Marketing Gap Score.

## Scoring

The Marketing Gap Score is calculated by application code, NOT by the LLM.

Current V1 scoring:

- SUPPORTED = 0 penalty
- INSUFFICIENT_INFORMATION = 0 penalty
- NOT_SUPPORTED = 1 penalty

Marketing Gap Score =
percentage of assessable claims that are NOT_SUPPORTED.

If there are no assessable claims, the score is null.

Keep scoring logic isolated and unit tested.

## Architecture

Keep V1 intentionally simple.

Do NOT introduce unless explicitly requested:

- RAG
- vector databases
- embeddings
- LangChain
- LlamaIndex
- MCP
- agents
- authentication
- databases
- unnecessary infrastructure

We will introduce these incrementally when they solve an actual problem.

## AI behavior

The model should:

- extract what is actually visible
- distinguish claims from factual nutrition information
- split combined marketing statements into independently assessable atomic claims
- use only supplied regulatory information for compliance evaluation
- avoid unsupported assumptions
- explicitly report insufficient information
- report a regulatory classification only when explicitly defined by supplied rules
- avoid medical or health recommendations

The model must not:

- declare a food healthy/unhealthy
- invent nutrition values
- invent FSSAI requirements
- infer missing label information
- treat the absence of an ingredient as regulatory proof unless supplied rules say it is sufficient
- make regulatory/legal determinations beyond the supplied criteria

## Code quality

Prefer simple, readable Python.

Keep model interaction, prompts, and deterministic business logic separated.

Use structured outputs rather than parsing free-form model responses.

All deterministic business logic must be unit testable without making API calls.

## Git workflow

Never make changes directly on `main`.

All work must happen on a feature branch.

Current feature branch:

feature/v1-claim-analyzer

Do not merge or push unless explicitly instructed.

Before making changes:

1. Inspect the current repository state.
2. Check the current branch.
3. Preserve existing work.

## Development philosophy

Build the smallest working version first.

Do not add abstractions, frameworks, infrastructure, or dependencies without a concrete requirement.

When uncertain, prefer asking or documenting the assumption rather than silently inventing behavior.
