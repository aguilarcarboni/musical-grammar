# Chord Calculator (Deliverable 3)

## Usage
- From the repo root: `python3 calculator/calculator.py songs/<song>.txt`
- Inputs must follow the project grammar (bars with optional meter, chords/NC/%, final `||`).
- The calculator first validates with the bundled parser (deliverable 2), then derives chord notes and prints the Fig. 3-style histogram with totals (ignores `%` bars for totals/output). Header columns are fixed width.
