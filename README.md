# FoodPharmer V1 Claim Analyzer

FoodPharmer checks whether marketing claims visible on a packaged-food image are supported by the FSSAI criteria you provide. It does not assess whether a food is healthy or unhealthy.

## Setup

Use Python 3.10 or newer, create a virtual environment, and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
```

## Usage

Put only the applicable FSSAI rules in a UTF-8 text file. The rules file is the sole regulatory source supplied to the model.

```bash
python main.py \
  --image /path/to/package.png \
  --rules /path/to/applicable-fssai-rules.txt
```

The command prints strict JSON with:

- `nutrition_facts`: facts visibly present on the label
- `claims`: every visible marketing claim with a `SUPPORTED`, `NOT_SUPPORTED`, or `INSUFFICIENT_INFORMATION` verdict
- `marketing_gap_score`: a locally calculated percentage, or `null` when no claim is assessable

`marketing_gap_score` is calculated in Python: `NOT_SUPPORTED / (SUPPORTED + NOT_SUPPORTED) * 100`. Claims with `INSUFFICIENT_INFORMATION` are excluded from both numerator and denominator.

Optionally select a different compatible OpenAI model:

```bash
python main.py --image /path/to/package.png --rules /path/to/rules.txt --model gpt-4.1-mini
```

## Tests

The scoring rules are unit tested without API calls:

```bash
python -m unittest discover -s tests -v
```

## V1 limitations

- Supported image formats are JPG, PNG, and WebP.
- The analyzer uses only visible image content and the supplied rules; it does not fill in missing label data or regulatory criteria.
- A verdict says whether supplied criteria support a visible marketing claim. It is not a health judgment, medical advice, or a legal/regulatory determination.
