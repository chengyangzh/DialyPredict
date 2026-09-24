# Data privacy and publication policy

## Zero-patient-data rule

This repository must never contain:

- raw or transformed clinical rows;
- names, medical-record numbers, outpatient identifiers, dates of birth, addresses, phone numbers, or other direct identifiers;
- stable or pseudonymous patient identifiers, hashes, HMAC values, or patient-level split assignments;
- clinical Excel, CSV, database, audio, image, or document exports;
- patient-level predictions, recommendations, feature vectors, or residuals;
- trained model weights, learned response surfaces, or serialized preprocessing objects derived from clinical data;
- real-data aggregate results that have not passed institutional disclosure review.

## Allowed content

- generic source code;
- empty configuration templates;
- documentation that contains no real-data statistics;
- deterministic unit tests using invented values;
- synthetic demonstration assets generated without fitting to clinical data.

## Required pre-push checks

Run:

```bash
python scripts/privacy_check.py .
pytest
```

The privacy check is a guardrail, not a substitute for institutional review. A human reviewer must inspect the complete Git diff before every push.

## Patent and disclosure caution

Repository visibility should remain private until the project team has completed its intellectual-property and institutional disclosure review. Removing data does not eliminate the risk of disclosing patentable methods.

