# Musical Grammar

## Concepts of Programming Languages

### Description

Musical Grammar is a project that takes a context-free grammar for popular-music chord charts and implements a parser and chord calculator in Python that validates songs written with that grammar, and calculates the chords for a given songs.

### Calculator (deliverable 3)
- Self-contained in `calculator/`.
- Sample songs: `songs/`
- Reference outputs: `reference_out/`
- Run the chord calculator (wide header, matches most refs): `python3 calculator/calculator.py <path-to-song-file>`
- Use compact header (matches the shorter-format refs): `python3 calculator/calculator.py --compact <path-to-song-file>`
- Input: a song file following the project grammar (bars, optional meter, chords/NC/% separators, song ends with `||`).
- Output: table like Fig. 3 in the spec, with per-chord pitch-class stars and a totals row (ignores `%` bar repeats for totals).

### Results
- Scored a ?? in the project.

### Created by [@aguilarcarboni](https://github.com/aguilarcarboni/) and [@axantillon](https://github.com/axantillon)
