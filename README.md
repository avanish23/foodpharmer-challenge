# FoodPharmer — Evidence-Driven Claim Analysis

An experimental prototype that asks one question about the marketing on a food
package:

> **Can this claim be substantiated using available evidence?**

This branch (`feature/evidence-driven-claim-analysis`) reworks the response
model from the ground up. It is deliberately **not** an FSSAI compliance
checker — FSSAI regulations are one of several evidence sources the system can
consult.

## Why not FSSAI-only?

The previous V1/V2 implementations conflated three different concepts into one
verdict per claim:

* is the claim *permitted* under FSSAI?
* is the claim *factually true* about this specific product?
* is the claim even *evaluable* (or is it subjective marketing)?

That collapse produced misleading verdicts. "50% less oil than other chips"
under a compliance-only model tends to land as NOT_SUPPORTED because the
system cannot find the rule — but the correct answer is *we cannot tell*,
which is a different reality.

This branch keeps four concerns separate: **Claim → Requirement → Evidence →
Verdict**.

## Architecture

Six deterministic stages wired end to end in `foodpharmer/pipeline.py`:

```
Image bytes
  ▼ [LLM vision]                    foodpharmer/extraction.py
PackageExtraction (claims[], nutrition_facts[], ingredients[], complete-flag)
  ▼ per claim [LLM]                 foodpharmer/normalization.py
NormalizedClaim (claim_type + typed payload)
  ▼ per claim [Python]              foodpharmer/requirements.py
list[EvidenceRequirement]
  ▼ per requirement [Python]        foodpharmer/evidence/*
list[GatheredEvidence]  (each: AVAILABLE | UNAVAILABLE)
  ▼ per claim [Python]              foodpharmer/resolvers/*
Verdict + Computation
  ▼
ClaimResult (the auditable JSON)
```

The LLM is used only for **language/vision reasoning**: reading the image,
splitting atomic claims, classifying, and (optionally) generating the human
reason. Everything downstream — requirement derivation, evidence gathering,
arithmetic, threshold comparisons — is plain Python.

## Verdicts

Four values, and the distinctions matter:

| Verdict | Meaning |
|---|---|
| `SUBSTANTIATED` | Available evidence supports the claim. |
| `CONTRADICTED` | Available evidence actually conflicts with the claim. |
| `UNSUBSTANTIATED` | The claim *may* be true, but evidence to verify it is unavailable. **Not the same as FALSE.** |
| `NON_FALSIFIABLE` | Subjective/vague marketing language — cannot be evaluated objectively. |

## Claim taxonomy

The eight types are a starting point, not final. Extend by adding a payload
type in `models.py`, a case in `requirements.py`, and a resolver.

| ClaimType | Example |
|---|---|
| `NUTRIENT_CONTENT` | "High Fibre", "Low Sugar" |
| `COMPARATIVE` | "50% less oil than other chips", "2x more protein" |
| `COMPOSITION` | "Made with 100% whole wheat" |
| `ABSENCE` | "No added sugar", "0% maida", "Trans fat free" |
| `QUANTITATIVE` | "10g protein per serve" |
| `SUPERLATIVE` | "India's #1 chips" |
| `SCIENTIFIC` | "Clinically proven to lower cholesterol" |
| `SUBJECTIVE_MARKETING` | "guilt-free", "wholesome goodness" |

## Evidence sources

Each source implements `foodpharmer.evidence.base.EvidenceSource`. A
requirement that no source can fulfill is still recorded — as UNAVAILABLE with
source `"none"` — so the audit trail is complete.

| Source | Requirement types | Status |
|---|---|---|
| `PackagingSource` | `NUTRIENT_VALUE`, `INGREDIENT_LIST`, `DECLARED_PERCENTAGE` | Real, reads the extraction |
| `FssaiRegulationSource` | `FSSAI_THRESHOLD` | Real, wraps `LocalFssaiRetriever` over PDFs in `data/fssai/` |
| `ComparatorProductSource` | `COMPARATOR_DATA` | Stub — always UNAVAILABLE |
| `MarketDataSource` | `MARKET_RANKING` | Stub — always UNAVAILABLE |

Add a new source by dropping a class into `foodpharmer/evidence/` and passing
it to `analyze()`.

## Comparative claims

The single most important behavior:

* A comparative claim with a **vague baseline** (`baseline_specified=False` —
  "other chips", "leading brands") is `UNSUBSTANTIATED`, never `CONTRADICTED`.
* A **specified baseline** without comparator data is still `UNSUBSTANTIATED`.
* Both available → resolver performs the arithmetic in Python and records a
  `Computation` block with inputs/result/passed.

The LLM never does the math.

## Running the demo

Offline (uses recorded fixtures under `tests/fixtures/`):

```bash
python main.py --provider fixture --case less_oil
```

Available cases: `high_fibre`, `less_oil`, `more_protein`, `whole_wheat`,
`guilt_free`.

Live OpenAI (requires `OPENAI_API_KEY` in the environment):

```bash
python main.py --provider openai --image images/some_pack.jpg
```

Re-record a fixture after prompt or schema changes:

```bash
python main.py --record --case less_oil --image images/less_oil.jpg
```

## Running tests

```bash
python -m pytest tests/ -v
```

Tests are fully offline — no API key required — because they run through
`FixtureProvider` and a small in-memory FSSAI retriever stub.

## Non-goals

This prototype intentionally does **not** build:

* RAG, vector databases, embeddings
* LangChain / LlamaIndex / MCP / agent frameworks
* Real comparator or market datasets
* A serving API, auth, or UI
* Database persistence
* Health / nutrition-quality scoring
* Web crawling

Response quality first, then infrastructure.

## Project layout

```
foodpharmer/
  models.py                Pydantic types — the JSON contract
  pipeline.py              Orchestrator
  extraction.py            Stage 1 — vision -> PackageExtraction
  normalization.py         Stage 2 -> NormalizedClaim
  requirements.py          Stage 3 -> EvidenceRequirement[]
  retrieval.py             Local FSSAI PDF retriever (ported from v2)
  ingredient_checks.py     Deterministic ingredient-list helper (from v2)
  providers/               LLMProvider Protocol + OpenAI + Fixture backends
  evidence/                Packaging / FSSAI / stubs
  resolvers/               One resolver per ClaimType — all deterministic
tests/
  fixtures/                5 canonical cases (extract.json + normalize.json + placeholder image)
  resolvers/               Resolver unit tests
  test_models.py, test_requirements.py, test_pipeline_fixtures.py
data/fssai/                FSSAI PDFs (real Compendium included)
main.py                    Demo CLI
```
