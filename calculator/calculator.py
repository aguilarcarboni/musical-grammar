import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple

# We parse songs into simple Python objects (Song -> Bars -> Chords), an AST (Abstract Syntax Tree) that is easier to
# work with than raw text. Load the bundled parser that lives next to this file so running `python calculator.py <song>`
# always works without extra setup.
parser_path = Path(__file__).resolve().parent / "parser.py"
spec = importlib.util.spec_from_file_location("calculator_parser", parser_path)
if not spec or not spec.loader:
    raise ImportError("Unable to load bundled parser.py")
submitted_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submitted_parser)

# Pitch-class helpers (0–11 pitch classes; letters map to white keys, accidentals adjust)
LETTER_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ACC_OFFSET = {"#": 1, "b": -1}

# Table I: base third/fifth intervals per quality (semitones from root)
QUALITY_INTERVALS = {
    "major": (4, 7),
    "minor": (3, 7),
    "aug": (4, 8),
    "dim": (3, 6),
    "power": (7,),
    "unison": tuple(),
}

# Table II: suspensions replace the third; keep/add fifths
SUSP_INTERVALS = {"sus2": (2, 7), "sus4": (5, 7), "sus24": (2, 5, 7)}

# Table III: extension intervals (semitones)
EXT_INTERVALS = {"6": 9, "7": 10, "9": 2, "11": 5, "13": 9}


class ParseError(Exception):
    pass


@dataclass
class Addition:
    accidental: Optional[str]
    target: str  # "5", "9", "11", "13"
    parenthesized: bool


@dataclass
class Chord:
    # One chord plus the attributes needed for note computation.
    label: str
    root_pc: int
    quality: Optional[str]  # '-', '+', 'o', '5', '1', or None (major)
    suspension: Optional[str]  # sus2/sus4/sus24
    number: Optional[str]  # 6,7,9,11,13 (with optional caret flag)
    caret: bool  # caret on number (raises 7th)
    addition: Optional[Addition]  # (alt) additions
    omission: Optional[str]  # no3/no5/no35
    bass_pc: Optional[int]  # inversion bass (added to notes)


@dataclass
class Bar:
    # A bar groups chords; is_repeat marks "%" bars the totals should skip.
    chords: List[Chord]
    is_repeat: bool  # True if bar was '%'


@dataclass
class Song:
    # A song is just an ordered list of bars.
    bars: List[Bar]


class CalculatorParser:
    """Lightweight structured parser (Song -> Bars -> Chords) used after the grammar validator."""

    def __init__(self, text: str):
        self.s = text
        self.pos = 0

    def parse(self) -> Song:
        # song := bar {bar} "|"  (final "|" closes the song)
        bars: List[Bar] = []
        self._skip_ws()
        bars.append(self._parse_bar())
        self._skip_ws()
        self._expect("|")
        self._skip_ws()
        while True:
            if self._peek() == "|":
                self._next()
                break
            bars.append(self._parse_bar())
            self._skip_ws()
            self._expect("|")
            self._skip_ws()
        self._skip_ws()
        if self._peek() is not None:
            raise ParseError(f"Unexpected input after song at position {self.pos}")
        return Song(bars=bars)

    # Low-level helpers ---------------------------------------------------
    def _peek(self) -> Optional[str]:
        return self.s[self.pos] if self.pos < len(self.s) else None

    def _next(self) -> str:
        c = self._peek()
        if c is None:
            raise ParseError("Unexpected end of input")
        self.pos += 1
        return c

    def _match(self, token: str) -> bool:
        if self.s.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def _expect(self, token: str) -> None:
        if not self._match(token):
            raise ParseError(f"Expected '{token}' at position {self.pos}")

    def _skip_ws(self) -> None:
        while self._peek() is not None and self._peek().isspace():
            self.pos += 1

    def _is_digit(self, ch: Optional[str]) -> bool:
        return ch is not None and ch.isdigit()

    # Grammar pieces ------------------------------------------------------
    def _parse_bar(self) -> Bar:
        # bar := [meter] chords "|"
        self._skip_ws()
        if self._is_digit(self._peek()):
            self._parse_meter()
        chords = self._parse_chords()
        return chords

    def _parse_meter(self) -> None:
        # meter := numerator "/" denominator
        self._parse_numerator()
        self._expect("/")
        self._parse_denominator()

    def _parse_numerator(self) -> int:
        digits = self._consume_digits()
        if digits is None:
            raise ParseError("Expected numerator")
        num = int(digits)
        if not (1 <= num <= 15):
            raise ParseError("Numerator out of range")
        return num

    def _parse_denominator(self) -> int:
        digits = self._consume_digits()
        if digits is None:
            raise ParseError("Expected denominator")
        den = int(digits)
        if den not in {1, 2, 4, 8, 16}:
            raise ParseError("Invalid denominator")
        return den

    def _consume_digits(self) -> Optional[str]:
        start = self.pos
        while self._is_digit(self._peek()):
            self.pos += 1
        if start == self.pos:
            return None
        return self.s[start:self.pos]

    def _parse_chords(self) -> Bar:
        self._skip_ws()
        if self._match("NC"):
            return Bar(chords=[], is_repeat=False)
        if self._peek() == "%":
            self._next()
            return Bar(chords=[], is_repeat=True)

        chords: List[Chord] = []
        while True:
            self._skip_ws()
            if self._peek() in {None, "|"}:
                break
            chords.append(self._parse_chord())
            self._skip_ws()
            if self._peek() in {None, "|"}:
                break
        if not chords:
            raise ParseError("Expected chord")
        return Bar(chords=chords, is_repeat=False)

    def _parse_chord(self) -> Chord:
        # chord := root [description] [bass]
        self._skip_ws()
        start = self.pos
        root_pc = self._parse_note()
        quality = self._parse_optional_quality()
        number, caret = self._parse_optional_number()
        addition = self._parse_optional_addition()
        suspension = self._parse_optional_suspension()
        omission = self._parse_optional_omission()
        if quality is not None and suspension is not None:
            raise ParseError("Quality and suspension cannot coexist")
        self._skip_ws()
        bass_pc = self._parse_optional_bass()
        label = self.s[start:self.pos].strip()
        return Chord(
            label=label,
            root_pc=root_pc,
            quality=quality,
            suspension=suspension,
            number=number,
            caret=caret,
            addition=addition,
            omission=omission,
            bass_pc=bass_pc,
        )

    def _parse_note(self) -> int:
        # note := letter [acc]
        letter = self._next()
        if letter not in LETTER_TO_PC:
            raise ParseError(f"Invalid note letter '{letter}' at position {self.pos}")
        acc = None
        if self._peek() in ACC_OFFSET:
            acc = self._next()
        pc = (LETTER_TO_PC[letter] + ACC_OFFSET.get(acc, 0)) % 12
        return pc

    def _parse_optional_quality(self) -> Optional[str]:
        c = self._peek()
        if c in {"-", "+", "o", "5"}:
            self._next()
            return c
        if c == "1":
            nxt = self.s[self.pos + 1] if self.pos + 1 < len(self.s) else None
            if nxt in {"1", "3"}:
                return None
            self._next()
            return "1"
        return None

    def _parse_optional_number(self) -> Tuple[Optional[str], bool]:
        # qnum := "6" | ["^"] "7" | ["^"] ext
        caret = False
        start = self.pos
        if self._peek() == "^":
            caret = True
            self._next()
        first = self._peek()
        if first is None or not first.isdigit():
            self.pos = start
            return None, False
        token = self._next()
        if token in {"6", "7", "9"}:
            if caret and token == "6":
                raise ParseError("^6 is invalid")
            return token, caret
        if token == "1" and self._peek() in {"1", "3"}:
            token += self._next()
            if token not in {"11", "13"}:
                self.pos = start
                return None, False
            return token, caret
        self.pos = start
        return None, False

    def _parse_optional_addition(self) -> Optional[Addition]:
        # add := alt | "(" alt ")"
        start = self.pos
        paren = False
        if self._peek() == "(":
            paren = True
            self._next()
        alt = self._parse_optional_alt()
        if alt is None:
            self.pos = start
            return None
        if paren:
            self._expect(")")
        acc, target = alt
        return Addition(accidental=acc, target=target, parenthesized=paren)

    def _parse_optional_alt(self) -> Optional[Tuple[Optional[str], str]]:
        start = self.pos
        acc = None
        if self._peek() in ACC_OFFSET:
            acc = self._next()
        c = self._peek()
        if c == "5":
            self._next()
            return acc, "5"
        if c == "9":
            self._next()
            return acc, "9"
        if c == "1" and self.pos + 1 < len(self.s) and self.s[self.pos + 1] in {"1", "3"}:
            tok = self.s[self.pos : self.pos + 2]
            self.pos += 2
            return acc, tok
        self.pos = start
        return None

    def _parse_optional_suspension(self) -> Optional[str]:
        if self._match("sus2"):
            if self._match("4"):
                return "sus24"
            return "sus2"
        if self._match("sus4"):
            return "sus4"
        return None

    def _parse_optional_omission(self) -> Optional[str]:
        if not self._match("no"):
            return None
        if self._match("3"):
            if self._match("5"):
                return "no35"
            return "no3"
        if self._match("5"):
            return "no5"
        raise ParseError("Invalid omission")

    def _parse_optional_bass(self) -> Optional[int]:
        self._skip_ws()
        if self._peek() != "/":
            return None
        self._next()
        self._skip_ws()
        return self._parse_note()


def compute_notes(chord: Chord) -> Set[int]:
    """Turn a parsed Chord into its pitch classes (0-11), respecting quality, extensions, adds, omissions, bass."""
    if chord.label == "NC":
        return set()

    notes: Set[int] = {chord.root_pc}
    base_intervals = _base_intervals(chord)
    base_intervals = _apply_omissions(base_intervals, chord.omission)
    notes |= {_add_interval(chord.root_pc, i) for i in base_intervals}

    seventh_state: Optional[str] = None  # "b7" or "maj7"
    if chord.number:
        # Extensions add intervals; 9/11/13 imply a 7th unless caret alters it.
        intervals, sev = _extension_intervals(chord.number, chord.caret, include_7th=True)
        for i in intervals:
            notes.add(_add_interval(chord.root_pc, i))
        seventh_state = sev or seventh_state

    if chord.addition:
        acc = chord.addition.accidental
        target = chord.addition.target
        offset = ACC_OFFSET.get(acc, 0)
        if target == "5":
            # Altered fifth substitutes the perfect fifth family.
            desired = (7 + offset) % 12
            for candidate in (6, 7, 8):
                notes.discard(_add_interval(chord.root_pc, candidate))
            notes.add(_add_interval(chord.root_pc, desired))
        else:
            # Additions (alt) with optional implicit 7th unless parenthesized.
            include_7th = target in {"9", "11", "13"} and not chord.addition.parenthesized
            intervals, sev = _extension_intervals(target, caret=False, include_7th=include_7th)
            adjusted = ((intervals[0] + offset) % 12, *intervals[1:])
            notes.add(_add_interval(chord.root_pc, adjusted[0]))
            if len(adjusted) > 1 and sev and seventh_state is None:
                notes.add(_add_interval(chord.root_pc, 10))
                seventh_state = sev if sev else seventh_state

    if chord.bass_pc is not None:
        notes.add(chord.bass_pc)

    return notes


def _base_intervals(chord: Chord) -> Set[int]:
    # Core third/fifth (or suspension) intervals keyed by chord quality/suspension.
    if chord.suspension:
        # Suspensions override the third; fifth(s) stay as defined in table.
        return set(SUSP_INTERVALS[chord.suspension])
    quality = chord.quality or "major"
    mapping = {"-": "minor", "+": "aug", "o": "dim", "5": "power", "1": "unison"}
    key = mapping.get(quality, "major")
    return set(QUALITY_INTERVALS[key])


def _apply_omissions(intervals: Set[int], omission: Optional[str]) -> Set[int]:
    # Remove 3rd/5th intervals when the chord explicitly omits them.
    if omission is None:
        return intervals
    intervals = set(intervals)
    if omission in {"no3", "no35"}:
        intervals.discard(3)
        intervals.discard(4)
    if omission in {"no5", "no35"}:
        intervals.discard(6)
        intervals.discard(7)
        intervals.discard(8)
    return intervals


def _extension_intervals(
    number: str, caret: bool, include_7th: bool
) -> Tuple[List[int], Optional[str]]:
    # Returns extension intervals and whether a 7th was included (for caret handling).
    if number == "6":
        return [EXT_INTERVALS["6"]], None
    if number == "7":
        val = 11 if caret else 10
        return [val], "maj7" if caret else "b7"
    if number in {"9", "11", "13"}:
        ext_interval = EXT_INTERVALS[number]
        intervals: List[int] = [ext_interval]
        sev_val = 11 if caret else 10
        if include_7th:
            intervals.append(sev_val)
            return intervals, "maj7" if caret else "b7"
        return intervals, None
    raise ParseError(f"Unhandled extension: {number}")


def _add_interval(root_pc: int, interval: int) -> int:
    return (root_pc + interval) % 12


def format_table(rows: List[Tuple[Set[int], str, bool]]) -> str:
    """Render the Fig. 3-style histogram with totals; rows carries notes, label, and whether to count totals."""
    labels = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B"]
    index_field = 4  # len like " 99."
    pad = " " * (index_field + 1)

    cell_width = 3

    header = pad + " ".join(f"{lab:>{cell_width}}" for lab in labels)
    divider = pad + " ".join(f"{'-':>{cell_width}}" for _ in labels)

    lines = [header, divider]
    totals = [0] * 12

    for idx, (notes, label, counts) in enumerate(rows, start=1):
        line = f"{idx:>3}. "
        cells = []
        for i in range(12):
            cell = "*" if i in notes else ""
            cells.append(f"{cell:>{cell_width}}")
            if counts and i in notes:
                totals[i] += 1
        line += " ".join(cells)
        line += f"  {label}"
        lines.append(line)

    lines.append(divider)
    totals_line = pad + " ".join(f"{val:>{cell_width}}" for val in totals)
    lines.append(totals_line)
    return "\n".join(lines)


def expand_song(song: Song) -> List[Tuple[Set[int], str, bool]]:
    """Flatten Song AST into row tuples, skipping repeated bars ('%') entirely."""
    rows: List[Tuple[Set[int], str, bool]] = []
    prev_chords: Optional[List[Chord]] = None
    for bar in song.bars:
        if bar.is_repeat:
            if prev_chords is None:
                raise ParseError("Repeat bar without previous bar")
            # Skip output entirely for repeated bars; totals are unaffected.
            continue
        chords = bar.chords
        prev_chords = chords
        counts = True
        for chord in chords:
            notes = compute_notes(chord)
            rows.append((notes, chord.label, counts))
    return rows


def load_song(path: str) -> Song:
    """Read a song file, validate with the submitted parser, then build a fresh AST for computation."""
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    # Validate with submitted parser; do not alter that code.
    if submitted_parser is None:
        raise ParseError("Bundled parser not found; ensure calculator/parser.py is present.")
    submitted_parser.ChordParser(content).parse_input()
    parser = CalculatorParser(content)
    return parser.parse()


def main(argv: List[str]) -> None:
    args = argv[1:]
    if len(args) != 1:
        print("Usage: python calculator.py <song-file>", file=sys.stderr)
        sys.exit(1)
    song_path = args[0]
    song = load_song(song_path)
    rows = expand_song(song)
    output = format_table(rows)
    print(output)
    _write_output(song_path, output)


def _write_output(song_path: str, output: str) -> None:
    """Persist the rendered table to ./out/<song_basename>_notes.txt so graders know it's computed output."""
    base_dir = Path(__file__).resolve().parent  # keep outputs inside calculator/
    out_dir = base_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{Path(song_path).stem}_notes.txt"
    out_file.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv)
