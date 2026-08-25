## Product Direction — Evidence-Driven Claim Analysis

The core product question is:

> Can a marketing claim made on food packaging be substantiated using available evidence?

FSSAI regulations are one evidence source, not the complete source of truth.

The system must distinguish between:
- regulatory compliance
- factual substantiation
- comparative claims
- non-falsifiable marketing language

The system must NOT equate FSSAI compliance with overall claim truthfulness.

### Claim verdicts

Use these conceptual verdicts:

- SUBSTANTIATED
  Evidence supports the claim.

- CONTRADICTED
  Available evidence directly conflicts with the claim.

- UNSUBSTANTIATED
  The claim may be true, but available evidence is insufficient to verify it.

- NON_FALSIFIABLE
  The statement is subjective or too vague to establish objectively.

Do not label a claim FALSE merely because it cannot be substantiated.

### Claim categories

Claims should be classified before evaluation.

Examples include:

- NUTRIENT_CONTENT
- COMPARATIVE
- COMPOSITION
- ABSENCE
- QUANTITATIVE
- SUPERLATIVE
- SCIENTIFIC
- SUBJECTIVE_MARKETING

The ontology may evolve as more real-world claims are analyzed.

### Evidence-driven architecture

The system should determine what evidence is required to evaluate each claim.

Examples:

"High fibre"
→ product fibre content + applicable FSSAI criterion

"50% less oil"
→ claimed comparison baseline + comparable measurement + product measurement

"2x more protein"
→ reference product + comparable protein measurements

"100% whole wheat"
→ ingredient/composition evidence

"India's #1"
→ authoritative market/ranking evidence and methodology

### Core principle

The LLM should not be the final authority.

Use deterministic application logic wherever the problem can be expressed deterministically, especially:
- arithmetic
- percentage comparisons
- threshold comparisons
- unit normalization
- evidence matching

The LLM should primarily be used for:
- extracting claims
- normalizing claims
- identifying evidence requirements
- interpreting retrieved evidence
- explaining conclusions

Never invent missing evidence.

If evidence is unavailable, explicitly report that it is unavailable.

---

## Current State

The backend pipeline is complete and merged to `main`. Read `README.md` for
the full architecture; the short version:

- Six-stage pipeline in `foodpharmer/pipeline.py`:
  `extract → normalize → derive_requirements → gather_evidence → resolve → assemble`
- LLM (`foodpharmer/providers/openai_provider.py`) is used only for vision
  extraction and claim classification. All arithmetic and verdicts run in
  deterministic Python resolvers under `foodpharmer/resolvers/`.
- CLI: `python main.py --provider openai --images front.jpg back.jpg` (multi-
  image, merged into one `PackageExtraction`). Compact human summary by
  default; `--json` for the full audit trail.
- 38 offline tests: `python -m pytest tests/ -v`
- Five canonical fixture cases under `tests/fixtures/` exercise every verdict
  path.

---

## Next Milestone — Web App (start a new session for this)

The next major workstream is a mobile-optimized web app around the existing
pipeline. Native apps are explicitly deferred — the browser handles camera
capture (`<input type="file" accept="image/*" capture="environment">`) and
distribution is zero-friction.

### MVP scope (roughly one week)

**Backend service** — thin FastAPI wrapper around the existing pipeline:
- `POST /analyze` — accepts 1..N multipart image uploads, returns the same
  `ClaimAnalysisResult` JSON the CLI produces today.
- `GET /cases/{name}` — optionally exposes fixture cases so the frontend has
  a demo mode without an OpenAI call.
- `OPENAI_API_KEY` stays in the server env — never ship it to the browser.
- Deploy target: Render / Railway / Fly.io. Pick one on cost/latency; all
  three are fine.

**Frontend** — one page, three states:
1. **Capture** — big "Take photo" button (rear camera), option to add more
   images (front + back), then Analyze.
2. **Analyzing** — spinner + honest copy ("Reading the label… this takes
   about 15 seconds").
3. **Results** — one card per claim:
   - Claim text
   - Colored verdict pill (green SUBSTANTIATED / red CONTRADICTED / grey
     UNSUBSTANTIATED / blue NON_FALSIFIABLE)
   - Reason line (the compact renderer already produces good copy)
   - "Show evidence" expander with the computation + evidence entries

Stack: Next.js + Tailwind, or Vite + React + Tailwind. Deploy frontend to
Vercel or Netlify.

### Explicitly NOT in v1

- Login / accounts
- History / saved products
- Sharing / social
- Ratings / feedback (add once there are real users)
- Native iOS/Android apps
- Push notifications, background sync, on-device inference

### Session-handoff prompt

When starting the frontend session, seed it with something like:

> The backend at `foodpharmer/` is done — see `README.md` for the architecture.
> Build a mobile-optimized web app around it. Start with a FastAPI wrapper
> around `foodpharmer.pipeline.analyze()` and a Next.js frontend that captures
> a photo (or accepts multiple), sends it to the API, and renders the
> `ClaimAnalysisResult` as cards. Read `README.md` and `CLAUDE.md` first.

---

## Backend Backlog (do alongside or before frontend work)

Concrete follow-ups worth doing on the backend — none block the web app, but
each improves the response quality visibly on real packs:

1. **Nutrient synonym map** in `foodpharmer/evidence/packaging.py`.
   Real labels say "Total Fat", not "oil"; "Total Sugars", not "sugar". The
   current `_keyword_from_description` heuristic misses these. Add a small
   dict of `{claim_word → nutrition-label alias(es)}` and search all aliases.
   Concrete miss today: `less_oil` fixture reports NUTRIENT_VALUE unavailable
   because "oil" doesn't match "Total Fat".

2. **Real `ComparatorProductSource`**. The stub always returns UNAVAILABLE,
   so comparative claims with specified baselines can never resolve. First
   version: a CSV of category averages (e.g. per-100g fat / protein / sugar
   for "chips", "biscuits", "instant noodles"), loaded once at startup, keyed
   on category. Even a hand-curated table with 10 categories unlocks the
   whole COMPARATIVE verdict path.

3. **Unit normalization module** (`foodpharmer/units.py`). Convert mg↔g,
   µg↔mg, per-serve↔per-100g using the declared serving size. Resolvers
   currently assume matching units; a "Sodium 198 mg per 100 g" vs. FSSAI's
   "0.12 g per 100 g" comparison is off by 1000× today. This is a
   correctness bug waiting for a real label to expose it.

4. **Extraction prompt hardening**. The product name still gets extracted as
   a COMPOSITION claim occasionally (e.g. "Ragi Kaju Pista Cookies"). The
   prompt already tells the model to exclude product/brand names — but a
   small negative-example section listing 3–4 real cases would help.

5. **Add a second FSSAI PDF** (Nutrition Labelling Regulations 2020) to
   `data/fssai/` so the retriever has broader coverage. The Compendium alone
   is claim-focused; the labelling regs cover disclosure obligations.

---

## Deferred — Evaluation Framework

Design was sketched during the pipeline work but not built. Worth doing as
soon as the frontend loop is closed and you have 100+ real users generating
real cases:

- `tests/eval/cases.yaml` — hand-labeled products (target 100 to start).
  Each case names an image, a list of expected claims, and each claim's
  expected `ClaimType` + `Verdict`.
- `tests/eval/runner.py` — runs the pipeline over every case in fixture mode
  (fast, deterministic) or live mode (real API calls); emits a metrics
  table.
- Metrics: verdict accuracy overall + per-`ClaimType`; 4×4 confusion matrix
  (the UNSUBSTANTIATED vs CONTRADICTED cell is the interesting one);
  classification accuracy; extraction recall/precision; determinism across
  N runs of the same case.
- Reports: CLI table on stdout + dated JSON in `tests/eval/reports/`.
- A `label` CLI to grow the case set: shows the pipeline's output, asks the
  human `y`/`n`/correct, appends to `cases.yaml`.

Data source for the initial 100 cases: **Open Food Facts** (India subset,
CC-BY, legally clean, ingredient + nutrition + images). **Not** Amazon /
Flipkart — bot-detected, ToS-hostile, and their listing images are marketing
shots, not back-of-pack.

Volume without an eval loop is optimizing the wrong axis. Build the loop
before you scale the corpus.

---

## Known Limitations (as of merge)

Not bugs — deliberate simplifications worth remembering:

- `ComparatorProductSource` and `MarketDataSource` are stubs. Comparative
  claims with specified baselines and superlatives always land as
  UNSUBSTANTIATED for now.
- FSSAI thresholds are a hand-curated table in
  `foodpharmer/resolvers/nutrient_content.py` (`_QUALIFIER_THRESHOLDS`).
  Retriever provides citations, not numeric values parsed from the PDF.
- Multi-image extraction costs ~2× vision tokens per additional image. Only
  the extraction call is affected; normalization and resolvers are
  unchanged.
- `temperature=0` on OpenAI is best-effort determinism, not a guarantee.
  Small run-to-run drift on extraction still happens.
