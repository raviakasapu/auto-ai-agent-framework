# Document Processing Playbook

Pattern for building agent systems that analyze, extract, and transform documents.

## Use Cases

- Contract analysis and extraction
- Invoice processing
- Resume parsing
- Report generation
- Document classification

## Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ DOCUMENT ORCHESTRATOR                                       │
│ - Classify document type                                    │
│ - Route to appropriate processor                            │
│ - Aggregate extraction results                              │
└─────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────────────────┐
         │                                          │
         ▼                                          ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│ EXTRACTION MANAGER          │    │ TRANSFORMATION MANAGER      │
│ - Entity extraction         │    │ - Format conversion         │
│ - Field identification      │    │ - Template filling          │
│ - Validation                │    │ - Report generation         │
└─────────────────────────────┘    └─────────────────────────────┘
         │                                          │
         ▼                                          ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│ Extraction Workers          │    │ Transformation Workers      │
│ - extract_text              │    │ - convert_format            │
│ - identify_fields           │    │ - apply_template            │
│ - validate_extraction       │    │ - generate_report           │
└─────────────────────────────┘    └─────────────────────────────┘
```

## Tool Categories

### Document Input
- `load_document` — Load PDF, DOCX, images
- `extract_text` — OCR and text extraction
- `split_pages` — Page-level processing

### Analysis Tools
- `classify_document` — Determine document type
- `identify_sections` — Find headers, paragraphs
- `extract_tables` — Table detection and extraction

### Extraction Tools
- `extract_entities` — Named entity recognition
- `extract_fields` — Form field extraction
- `extract_key_value_pairs` — Key-value detection

### Transformation Tools
- `convert_format` — PDF → DOCX, etc.
- `apply_template` — Fill document templates
- `generate_summary` — Document summarization

## Policy Patterns

### Confidence Thresholds
```yaml
policies:
  extraction:
    config:
      min_confidence: 0.85
      require_human_review: true
      review_threshold: 0.95
```

### Multi-Stage Validation
```yaml
planning_prompt: |
  For each extraction:
  1. Extract with primary method
  2. Cross-validate with secondary method
  3. Flag low-confidence results for review
```

## Context Services

### Document Store
- Manages document uploads
- Provides page-level access
- Caches extraction results

### Template Registry
- Stores output templates
- Provides field mappings
- Manages versioning

## Structured Output

```python
class ExtractionResult(FinalResponse):
    operation: str = "extraction_complete"
    payload: dict = {
        "document_id": "doc-123",
        "document_type": "invoice",
        "fields": {
            "invoice_number": {"value": "INV-2024-001", "confidence": 0.98},
            "total_amount": {"value": 1250.00, "confidence": 0.95},
            "vendor": {"value": "Acme Corp", "confidence": 0.92}
        },
        "requires_review": ["vendor"]
    }
    human_readable_summary: str = "Extracted 3 fields from invoice. Vendor field flagged for review."
```

## Implementation Notes

This playbook is a pattern guide. To implement:

1. Create document input tools using your preferred OCR/extraction library
2. Design extraction workers for each document type
3. Configure confidence-based HITL policies
4. Set up document and template stores
5. Wire Phoenix tracing for extraction metrics

