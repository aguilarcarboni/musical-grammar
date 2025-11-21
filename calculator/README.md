# Chord Calculator (Deliverable 3)

## Usage
- From the root: `python3 calculator.py songs/<song>.txt`
- Inputs must follow the project grammar (bars with optional meter, chords/NC/%, final `||`).
- The calculator first validates with the bundled parser (deliverable 2), then uses an internal AST builder to derive chord notes and print the Fig. 3-style histogram with totals (ignores `%` bars for totals/output). Header columns are fixed width.
- Two passes are used intentionally: keep the submitted parser unchanged for validation, then parse again for computation; overhead is negligible on these inputs.

## Notes
- Requires Python 3 only; run from the root.
- Command: `python3 calculator.py songs/<song>.txt`
- Output: printed histogram and a file at `calculator/out/<song_basename>_notes.txt`.
- To check against provided answers, compare the `_notes` file to the corresponding file in `reference_out/` (note/star pattern should match; formatting can differ).
