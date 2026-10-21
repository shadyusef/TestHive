#!/usr/bin/env bash
# Converts a module's requirement documents (text, PDF, Word, Excel, CSV, OpenAPI/Swagger, images) into text for the analyst.
# Usage: bash scripts/ingest.sh <MODULE> [--mask]
#   Reads requirements/sources/<module>/ (or requirements/sources/ when there is no module folder).
#   Writes analysis/sources-text/<MODULE>/<file>.md (with the source path on line 1) and index.csv.
#   --mask   hides personal data first (same rules as scripts/mask.sh); images are blacked out with OCR.
# Images are not converted: Claude reads them directly. Old .doc files must be saved as .docx first.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/ingest.py" "$@"
