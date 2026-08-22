# FoodPharmer V2 Claim Analyzer

FoodPharmer checks whether marketing claims visible on a packaged-food image are supported by applicable FSSAI criteria in locally supplied official documents. It does not assess whether a food is healthy or unhealthy.

## What changed in V2

V1 required a rules text file for each analysis. V2 reads local official FSSAI PDF documents, extracts page text, splits it into page-preserving chunks, and retrieves relevant chunks for each detected claim. The model evaluates a claim only against those retrieved chunks, which are included in the JSON response as `fssai_evidence`.

This is intentionally lightweight retrieval: deterministic keyword overlap over local chunks. It uses no embeddings, vector database, LangChain, or LlamaIndex.

## Setup

Use Python 3.10 or newer, create a virtual environment, and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
```

## Add official FSSAI documents

Place official FSSAI PDF documents under [data/fssai](/Users/avanish.patil/foodpharmer/data/fssai). Documents may be organised in subdirectories. They are read locally and are ignored by Git. See [data/fssai/README.md](/Users/avanish.patil/foodpharmer/data/fssai/README.md) for source requirements.

During ingestion, FoodPharmer extracts each PDF page's text, detects simple section or schedule headings, and splits text into sensible chunks without crossing page boundaries. Each chunk retains its document, local source path, page number, section, and verbatim text.

## Usage

```bash
python main.py \
  --image /path/to/package.png \
  --fssai-dir data/fssai
```

`--fssai-dir` is optional and defaults to `data/fssai`.

The command prints strict JSON with:

- `nutrition_facts`: facts visibly present on the label
- `claims`: every visible marketing claim, split into independently assessable atomic claims, with a `SUPPORTED`, `NOT_SUPPORTED`, or `INSUFFICIENT_INFORMATION` verdict
- `claims[].fssai_evidence`: exact retrieved FSSAI chunks used for that claim, including document and page metadata
- `claims[].ingredient_list_check`: a separate factual check for applicable `0% ingredient` claims; it reports `LISTED`, `NOT_LISTED`, or `INSUFFICIENT_INFORMATION` and never changes the FSSAI verdict or score
- `regulatory_classifications`: classifications explicitly defined by the supplied rules and evaluated using visible package facts; these are not health scores and do not affect scoring
- `marketing_gap_score`: a locally calculated percentage, or `null` when no claim is assessable

`marketing_gap_score` is calculated in Python: `NOT_SUPPORTED / (SUPPORTED + NOT_SUPPORTED) * 100`. Claims with `INSUFFICIENT_INFORMATION` are excluded from both numerator and denominator.

Optionally select a different compatible OpenAI model:

```bash
python main.py --image /path/to/package.png --model gpt-4.1-mini
```

## Tests

The scoring, document loading, chunking, retrieval, metadata preservation, and
claim evaluation flow are unit tested without API calls:

```bash
python -m unittest discover -s tests -v
```

## Limitations

- Supported image formats are JPG, PNG, and WebP.
- Only locally supplied PDF documents are used as the regulatory source. If no relevant chunk is retrieved, the claim receives `INSUFFICIENT_INFORMATION`.
- Keyword retrieval can miss terminology that is phrased very differently from the package claim; it is deliberately simple and replaceable.
- The analyzer uses only visible image content and retrieved FSSAI text; it does not fill in missing label data or regulatory criteria.
- An ingredient's absence is label evidence, not proof that a claim meets a regulatory criterion unless the supplied rules explicitly make it sufficient.
- A `0% ingredient` claim can include an ingredient-list check only when the complete ingredient list is visible. This check is label consistency evidence, not FSSAI compliance evidence, and has no effect on the Marketing Gap Score.
- A classification such as `high in sugar` is included only when the supplied rules define it and visible nutrition facts permit its evaluation. It is not a health judgment.
- A verdict says whether retrieved criteria support a visible marketing claim. This is an educational prototype, not a health judgment, medical recommendation, or legal/regulatory determination.
