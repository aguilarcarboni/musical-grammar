import os
import sys


class ParserError(Exception):
    pass


class ChordParser:
    def __init__(self, input_str):
        self.s = input_str
        self.pos = 0

    def peek(self):
        if self.pos < len(self.s):
            return self.s[self.pos]
        return None

    def next(self):
        c = self.peek()
        if c is not None:
            self.pos += 1
        return c

    def expect(self, expected):
        actual = self.next()
        if actual != expected:
            raise ParserError(f"Expected '{expected}' but got '{actual}' at position {self.pos}")

    def skip_ws(self):
        while self.peek() == " " or self.peek() == "\t" or self.peek() == "\n":
            self.next()

    def is_digit(self, c):
        return c is not None and "0" <= c <= "9"

    def parse_input(self):
        self.skip_ws()
        self.parse_song()
        self.skip_ws()
        if self.pos != len(self.s):
            raise ParserError(f"Extra input after song at position {self.pos}")
        return True

    def parse_song(self):
        self.parse_bar()
        while True:
            self.skip_ws()
            if self.peek() == "|":
                self.expect("|")
                return
            else:
                self.parse_bar()

    def parse_bar(self):
        self.skip_ws()
        c = self.peek()
        if self.is_digit(c):
            self.parse_meter()
        self.parse_chords()
        self.skip_ws()
        self.expect("|")

    def parse_meter(self):
        num = self.parse_numerator()
        self.expect("/")
        den = self.parse_denominator()

    def parse_numerator(self):
        num_str = ""
        while self.is_digit(self.peek()):
            num_str += self.next()
        if not num_str:
            raise ParserError("Expected numerator")
        num = int(num_str)
        if not (1 <= num <= 15):
            raise ParserError("Numerator out of range")
        return num

    def parse_denominator(self):
        den_str = ""
        while self.is_digit(self.peek()):
            den_str += self.next()
        if not den_str:
            raise ParserError("Expected denominator")
        den = int(den_str)
        if den not in [1, 2, 4, 8, 16]:
            raise ParserError("Denominator invalid")
        return den

    def parse_chords(self):
        self.skip_ws()
        if self.s[self.pos : self.pos + 2] == "NC":
            self.pos += 2
            return
        elif self.peek() == "%":
            self.next()
            return
        else:
            self.parse_chord()
            while True:
                self.skip_ws()
                c = self.peek()
                if c == "|" or c is None:
                    break
                self.parse_chord()

    def parse_chord(self):
        self.parse_root()
        self.parse_description()
        if self.peek() == "/":
            self.parse_bass()

    def parse_root(self):
        self.parse_note()

    def parse_note(self):
        self.parse_letter()
        if self.peek() in ("#", "b"):
            self.parse_acc()

    def parse_letter(self):
        c = self.next()
        if c not in "ABCDEFG":
            raise ParserError(f"Invalid letter '{c}'")
        return c

    def parse_acc(self):
        c = self.next()
        if c not in ("#", "b"):
            raise ParserError(f"Invalid accidental '{c}'")
        return c

    def parse_description(self):
        has_qual = self.parse_optional_qual()
        self.parse_optional_qnum()
        self.parse_optional_add()
        has_sus = self.parse_optional_sus()
        self.parse_optional_omit()
        if has_qual and has_sus:
            raise ParserError("qual and sus cannot coexist")

    def parse_optional_qual(self):
        c = self.peek()
        if c in ("-", "+", "o", "5"):
            self.next()
            return True
        elif c == "1":
            next_pos = self.pos + 1
            next_c = self.s[next_pos] if next_pos < len(self.s) else None
            if next_c in ("1", "3"):
                return False
            else:
                self.next()
                return True
        return False

    def parse_optional_qnum(self):
        start_pos = self.pos
        caret = False
        c = self.peek()
        if c == "^":
            caret = True
            self.next()
            c = self.peek()
        if self.is_digit(c):
            num_str = self.next()
            if num_str in ("6", "7", "9"):
                if caret and num_str == "6":
                    self.pos = start_pos
                    return False
            elif num_str == "1":
                c = self.peek()
                if c in ("1", "3"):
                    num_str += self.next()
                else:
                    self.pos = start_pos
                    return False
            else:
                self.pos = start_pos
                return False
            if num_str == "6" and caret:
                raise ParserError("^6 invalid")
            return True
        self.pos = start_pos
        return False

    def parse_optional_add(self):
        start_pos = self.pos
        in_paren = False
        if self.peek() == "(":
            in_paren = True
            self.next()
        if not self.parse_optional_alt():
            self.pos = start_pos
            return False
        if in_paren:
            self.expect(")")
        return True

    def parse_optional_alt(self):
        start_pos = self.pos
        if self.peek() in ("#", "b"):
            self.next()
        c = self.peek()
        if c == "5":
            self.next()
            return True
        elif c == "9":
            self.next()
            return True
        elif c == "1":
            self.next()
            c = self.peek()
            if c in ("1", "3"):
                self.next()
                return True
        self.pos = start_pos
        return False

    def parse_optional_sus(self):
        if self.s[self.pos : self.pos + 3] == "sus":
            self.pos += 3
            c = self.peek()
            if c == "2":
                self.next()
                if self.peek() == "4":
                    self.next()
                return True
            elif c == "4":
                self.next()
                return True
        return False

    def parse_optional_omit(self):
        if self.s[self.pos : self.pos + 2] == "no":
            self.pos += 2
            c = self.peek()
            if c == "3":
                self.next()
                if self.peek() == "5":
                    self.next()
                return True
            elif c == "5":
                self.next()
                return True
        return False

    def parse_bass(self):
        self.expect("/")
        self.parse_note()


def main():
    base_dir = os.path.dirname(__file__)
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base_dir, "songs")
    if os.path.isfile(target):
        file_paths = [target]
    else:
        files = os.listdir(target)
        file_paths = [os.path.join(target, fname) for fname in files]
    print("--------------------------------")
    for path in file_paths:
        with open(path, "r") as f:
            file_name = f.name.split("/")[-1].split(".")[0]
            print("Parsing song: ", file_name)
            input_content = f.read()
            parser = ChordParser(input_content)
            try:
                parser.parse_input()
                print("Song valid.")
            except ParserError as e:
                print(f"Song invalid: {e}")
        print("--------------------------------")


if __name__ == "__main__":
    main()
