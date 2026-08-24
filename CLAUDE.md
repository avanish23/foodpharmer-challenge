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