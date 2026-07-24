"""Trial-Ledger offline data pipeline.

The drug record is the atomic unit (see CLAUDE.md). This package is the single
source of truth for its shape: `schema.py` (Pydantic) drives validation, the
authoring structured-output contract, and the generated TypeScript frontend
types. Python owns the schema; the TS frontend follows via `gen_types`.
"""
