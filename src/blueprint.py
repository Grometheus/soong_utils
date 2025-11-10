# This file is part of the Grometheus project
# Copyright (C) PsychedelicPalimpsest - 2025
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
This file acts as a basic parser and evaluator for the Android.bp (Blueprint)
files. 
"""




from io import StringIO

from string import ascii_letters, digits, whitespace
from typing import TextIO, Type, cast, TypeAlias


WORD_LETTERS = set(ascii_letters + "_" + digits)
DIGITS_SET = set(digits)
WHITESPACE_SET = set(whitespace)



class BlueprintState:
    _variables : dict[str, 'BPType_Base']
    _text_blob : str


    
    def __init__(self, text_blob : str) -> None:
        self._variables = {}
        self._text_blob = text_blob

    def get_variable(self, variable_name : str) -> 'BPType_Base | None':
        return self._variables.get(variable_name)
    def set_variable(self, name : str, value : 'BPType_Base'):
        self._variables[name] = value

    def evaluate(self):
        return {
            k: v.evaluate(self)
            for k, v in self._variables.items() 
        }




def read_ascii_group(io: StringIO, valid_letters: set) -> str:
    word = ""
    while len(c := io.read(1)) and c in valid_letters:
        word += c

    if 0 != len(c):
        io.seek(io.tell() - 1)

    return word

def skip_ascii_whitespace(io: StringIO):
    while len(c := io.read(1)) and c in whitespace:
        pass

    if 0 != len(c):
        io.seek(io.tell() - len(c))


class BP_ParseError(Exception):
    def __init__(self, parse_ctx: StringIO, message: str) -> None:
        error_pos = parse_ctx.tell()

        our_msg = f"A parsing error has occured! {message}\n"

        line_cnt = 0
        col_cnt = 0
        curr_line = ""

        parse_ctx.seek(0)
        while error_pos > parse_ctx.tell():
            c = parse_ctx.read(1)
            if c == "\n":
                line_cnt += 1
                col_cnt = 0
                curr_line = ""
            else:
                col_cnt += 1
                curr_line += c

        while len(c := parse_ctx.read(1)) and c != "\n":
            curr_line += c

        our_msg += curr_line + "\n"
        our_msg += " " * col_cnt + "^\n"
        our_msg += f"aka: {line_cnt}:{col_cnt}"

        parse_ctx.seek(error_pos)

        super().__init__(our_msg)

class BP_EvalError(BP_ParseError):
    def __init__(self, parse_ctx: StringIO | None, message: str) -> None:
        if parse_ctx is not None:
            super().__init__(parse_ctx, message)
        else:
            Exception.__init__(self, message)




EVAL_VALUE: TypeAlias =  int | bool | str | list[str] | dict[str, "EVAL_VALUE"]



class BPType_Base:
    # Writes the string contents to the blueprint format
    #
    # Note:    Indentation level takes the current amount of indents
    # Note 2:  Assumes that any indentation for this value has already been printed
    def serialize(self, indentation_level=0) -> str:
        raise NotImplemented

    # Parse a blueprint formatted type from a StringIO.
    #
    # Note:     The io must be be currently at the start of the value
    @classmethod
    def deserialize(cls, io: StringIO) -> "BPType_Base":
        raise NotImplemented

    @classmethod
    def test(cls, io: StringIO) -> bool:
        raise NotImplemented


    # Take the BPType and translate it into a more pythonic value, defined by method
    def evaluate(self, state : BlueprintState) -> EVAL_VALUE:
        raise NotImplemented


class BPType_Variable(BPType_Base):
    _value: str

    def __init__(self, value: str) -> None:
        self._value = value

    def serialize(self, indentation_level=0) -> str:
        return self._value

    @classmethod
    def _test(cls, word: str) -> bool:
        return bool(word)

    @classmethod
    def test(cls, io: StringIO) -> bool:
        word = read_ascii_group(io, WORD_LETTERS)
        io.seek(io.tell() - len(word))
        return bool(word)

    @classmethod
    def deserialize(cls, io: StringIO) -> "BPType_Base":
        word = read_ascii_group(io, WORD_LETTERS)
        if not cls._test(word):
            io.seek(io.tell() - len(word))
            raise BP_ParseError(io, "Invalid variable name")

        return cls(word)
    
    def evaluate(self, state: BlueprintState):
        return state.get_variable(self._value).evaluate(state)
    def name(self):
        return self._value


class BPType_Bool(BPType_Base):
    _value: bool

    def __init__(self, value: bool) -> None:
        self._value = value

    def serialize(self, indentation_level=0) -> str:
        return str(self._value).lower()

    @classmethod
    def deserialize(cls, io: StringIO) -> BPType_Base:
        word = read_ascii_group(io, WORD_LETTERS)
        if not cls._test(word):
            io.seek(io.tell() - len(word))
            raise BP_ParseError(
                io, f"Boolean MUST be either true or false, not '{word}'"
            )
        return cls(word == "true")

    @classmethod
    def _test(cls, word: str) -> bool:
        return word in {"true", "false"}

    @classmethod
    def test(cls, io: StringIO) -> bool:
        word = read_ascii_group(io, WORD_LETTERS)

        ret = cls._test(word)
        io.seek(io.tell() - len(word))

        return ret

    def evaluate(self, state: BlueprintState) -> EVAL_VALUE:
        return self._value 


class BPType_Int(BPType_Base):
    _value: int

    def __init__(self, value: int) -> None:
        self._value = value

    def serialize(self, indentation_level=0) -> str:
        return str(self._value)

    @classmethod
    def _test(cls, word: str) -> bool:
        return len(word) != 0 and all(c in DIGITS_SET for c in word)

    @classmethod
    def test(cls, io: StringIO) -> bool:
        word = read_ascii_group(io, DIGITS_SET)

        ret = cls._test(word)
        io.seek(io.tell() - len(word))

        return ret

    @classmethod
    def deserialize(cls, io: StringIO) -> "BPType_Base":
        word = read_ascii_group(io, DIGITS_SET)
        print([word])
        if not cls._test(word):
            io.seek(io.tell() - len(word))
            raise BP_ParseError(io, f"Cannot parse int: {word}")
        return cls(int(word))

    def evaluate(self, state: BlueprintState) -> EVAL_VALUE:
        return self._value


NEWLINE_THRESHOLD = 32


class BPType_String(BPType_Base):
    _value: str

    def __init__(self, value: str) -> None:
        self._value = value

    def serialize(self, indentation_level=0) -> str:
        return f'"{self._value}"'


    def evaluate(self, state: BlueprintState) -> EVAL_VALUE:
        return self._value.replace('\\"', '"')

    @classmethod
    def test(cls, io: StringIO) -> bool:
        c = io.read(1)
        io.seek(io.tell() - len(c))

        return c == '"'

    @classmethod
    def deserialize(cls, io: StringIO) -> "BPType_Base":
        if not cls.test(io):
            raise BP_ParseError(io, "Not a string")

        _ = io.read(1)

        val = ""
        is_escaped = False
        while bool(c := io.read(1)):
            if c == '"' and not is_escaped:
                break

            is_escaped = c == "\\"
            val += c

        return cls(val)


class BPType_StringList(BPType_Base):
    _value: list[BPType_String]

    def __init__(self, value: list[BPType_String]) -> None:
        self._value = value

    @classmethod
    def from_list(cls, value: list[str]) -> "BPType_StringList":
        return cls([BPType_String(s) for s in value])


    def evaluate(self, state: BlueprintState) -> EVAL_VALUE:
        return cast(list[str], [v.evaluate(state) for v in self._value])

    @classmethod
    def test(cls, io: StringIO) -> bool:
        c = io.read(1)
        io.seek(io.tell() - len(c))

        return c == "["

    def serialize(self, indentation_level=0) -> str:
        strs = [c.serialize(indentation_level + 1) for c in self._value]

        if sum((len(s) + 2 for s in strs)) > NEWLINE_THRESHOLD:
            nl = "\n" + "\t" * (indentation_level)
            return f"[{nl}\t{  f',{nl}\t'.join(strs) }{nl}]"
        else:
            return "[" + ", ".join(strs) + "]"

    @classmethod
    def deserialize(cls, io: StringIO) -> "BPType_Base":
        c = io.read(1)
        if c != "[":
            io.seek(io.tell() - 1)
            raise BP_ParseError(io, "Not a valid list")
        expecting_ctrl = False
        value = []

        while True:
            skip_ascii_whitespace(io)
            c = io.read(1)

            if c == "]":
                break

            if expecting_ctrl:
                if c == ",":
                    expecting_ctrl = False
                    continue
                else:
                    io.seek(io.tell() - 1)
                    raise BP_ParseError(io, "Invalid charictor found between strings")
            else:

                io.seek(io.tell() - 1)
                if c != '"':
                    raise BP_ParseError(
                        io, "Invalid charictor found while expecting string"
                    )
                value.append(BPType_String.deserialize(io))
                expecting_ctrl = True

        return cls(value)


class BPType_Map(BPType_Base):
    _value: list[tuple[BPType_Variable, BPType_Base]]

    def __init__(self, value: list[tuple[BPType_Variable, BPType_Base]]) -> None:
        self._value = value


    def evaluate(self, state: BlueprintState) -> EVAL_VALUE:
        return {
            k.name() : v.evaluate(state)
            for k, v in self._value
        }

    @classmethod
    def test(cls, io: StringIO) -> bool:
        c = io.read(1)
        io.seek(io.tell() - len(c))

        return c == "{"

    def serialize(self, indentation_level=0) -> str:
        pairs = (
            (k.serialize(indentation_level + 1), v.serialize(indentation_level + 1))
            for k, v in self._value
        )

        lines = [f"{k}: {v}" for k, v in pairs]

        if sum(len(l) for l in lines) > NEWLINE_THRESHOLD:
            nl = "\n" + indentation_level * "\t"

            return "{" + nl + f", {nl}\t".join(lines) + nl + "}"
        else:
            return "{" + ", ".join(lines) + "}"

    @classmethod
    def deserialize(cls, io: StringIO) -> "BPType_Base":
        c = io.read(1)
        if c != "{":
            io.seek(io.tell() - len(c))
            raise BP_ParseError(io, "Not a map!")
        values = []
        while True:
            skip_ascii_whitespace(io)
            c = io.read(1)

            if c == "}":
                break
            io.seek(io.tell() - len(c))

            if not c:
                raise BP_ParseError(io, "Unexpected EOF")

            if not BPType_Variable.test(io):
                raise BP_ParseError(io, "Invalid key")

            key = BPType_Variable.deserialize(io)

            skip_ascii_whitespace(io)

            c = io.read(1)

            if c != ":":
                io.seek(io.tell() - len(c))
                raise BP_ParseError(
                    io, "Must use a ':' to seperate key and value in maps"
                )

            skip_ascii_whitespace(io)

            value = BP_parse_value(io)

            values.append((key, value))

            skip_ascii_whitespace(io)

            c = io.read(1)

            if c == "}":
                break
            if c != ",":
                io.seek(io.tell() - len(c))
                raise BP_ParseError(io, "Invalid charictor after map value")

        return cls(values)


class BPType_AddOp(BPType_Base):
    _oprand1: BPType_Base
    _oprand2: BPType_Base

    SUPPORTED_ADD_TYPES = [BPType_Int, BPType_String, BPType_StringList, BPType_Map]

    def __init__(self, oprand1: BPType_Base, oprand2: BPType_Base) -> None:
        self._oprand1 = oprand1
        self._oprand2 = oprand2

    @classmethod
    def deserialize(cls, io: StringIO) -> "BPType_Base":
        raise NotImplementedError("Cannot parse from a raw AddOp. ")

    def serialize(self, indentation_level=0) -> str:
        return f"{self._oprand1.serialize(indentation_level)} + {self._oprand2.serialize(indentation_level)}"

    @classmethod
    def test(cls, io: StringIO) -> bool:
        raise NotImplementedError(
            "An add op cannot be tested as it cannot be deserialized."
        )

    @classmethod
    def is_addop(cls, io: StringIO) -> bool:
        c = io.read(1)
        io.seek(io.tell() - len(c))

        return c == "+"

    @classmethod
    def join(cls, previous: BPType_Base, io: StringIO) -> "BPType_AddOp":
        if not (
            any(isinstance(previous, c) for c in cls.SUPPORTED_ADD_TYPES)
            or isinstance(previous, cls)
        ):
            raise BP_ParseError(
                io,
                "Invalid add operation. Initial type must be and int, string, list of strins, or map. ",
            )
        if (c := io.read(1)) != "+":
            io.seek(io.tell() - len(c))
            raise BP_ParseError(io, "Not an add op")
        skip_ascii_whitespace(io)

        c = BP_identify(io)
        if not c in cls.SUPPORTED_ADD_TYPES:
            raise BP_ParseError(
                io,
                "Invalid add operation. Initial type must be and int, string, list of strins, or map. ",
            )
        return cls(previous, c.deserialize(io))


    def evaluate(self, state: BlueprintState) -> EVAL_VALUE:
        or1 = self._oprand1.evaluate(state)
        or2 = self._oprand2.evaluate(state)

        if type(or1) is not type(or2):
            raise BP_EvalError(None, f"Cannot add between {type(or1)} and {or2}, aka: \n\t{self._oprand1.serialize(1)} \n and \n\t {self._oprand2.serialize(1)}")
        if type(or1) is str:
            return or1 + cast(str, or2)
        if type(or1) is int:
            return or1 + cast(int, or2)
        if type(or1) is list:
            return or1 + cast(list[str], or2)
        if type(or1) is dict:
            return {**or1, **cast(dict, or2)}


        assert False, "This should never happen"




def BP_parse_value(io: StringIO) -> BPType_Base:
    c = BP_identify(io)
    if c is None:
        raise BP_ParseError(io, "Value expected.")
    val = c.deserialize(io)

    skip_ascii_whitespace(io)
    while BPType_AddOp.is_addop(io):
        val = BPType_AddOp.join(val, io)
        skip_ascii_whitespace(io)
    return val


# Most specific to least specific
RAW_TYPES = [
    BPType_Bool,
    BPType_StringList,
    BPType_Map,
    BPType_Int,
    BPType_String,
    BPType_Variable,
]


def BP_identify(io: StringIO) -> Type[BPType_Base] | None:
    for t in RAW_TYPES:
        if t.test(io):
            return t



def ascii_find(io: StringIO, value : str) -> None | str:
    found = ""
    while len(value) == len(slab := io.read(len(value))) and slab != value:
        found += value[0]
        io.seek(io.tell() - len(slab) + 1)

    return found if slab == value else None






class BlueprintFile:
    _rules : list[tuple[str, EVAL_VALUE]]
    _state : BlueprintState



    _evaluated_variables : dict[str, EVAL_VALUE]


    def __init__(self, io : StringIO) -> None:
        self._state = BlueprintState(io.read())
        self._rules = []

        io.seek(0)

        skip_ascii_whitespace(io)

        while True:
            skip_ascii_whitespace(io)

            c = io.read(1)
            io.seek(io.tell() - len(c))

            if not c:
                break

            if c == '/':
                comment_prefix = io.read(2)
                # Currently we just discard the comments
                if comment_prefix == "//":
                    _ = ascii_find(io, "\n")
                    continue
                elif comment_prefix == "/*":
                    _ = ascii_find(io, "*/")

                    before_pos = io.tell()
                    value = ascii_find(io, "\n")

                    if value is not None and value.strip():
                        io.seek(before_pos)
                        raise BP_ParseError(io, "Nothing can follow comments!")
                    continue
                else:
                    io.seek(io.tell() - len(comment_prefix))
                    raise BP_ParseError(io, "Invalid syntax")

            if not c in ascii_letters:
                raise BP_ParseError(io, "Invalid syntax")

            name = cast(BPType_Variable, BPType_Variable.deserialize(io))

            line_start = io.tell()
            skip_ascii_whitespace(io)

            c = io.read(2)
            io.seek(io.tell() - len(c))

            if c[0] == '=' or c == "+=":
                io.seek(io.tell() + (1 if c[0] == "=" else 2))
                skip_ascii_whitespace(io)

                value = BP_parse_value(io)

                if c[0] == '=':
                    if self._state.get_variable(name.name()) is not None:
                        io.seek(line_start)
                        raise BP_EvalError(io, f"Cannot set variable '{name.name()}' as it is already defined")
                    self._state.set_variable(name.name(), value)
                else:
                    old_value = self._state.get_variable(name.name())
                    if old_value  is None:
                        io.seek(line_start)
                        raise BP_EvalError(io, f"Cannot add to variable '{name.name()}' as it is NOT already defined")

                    self._state.set_variable(
                        name.name(),
                        BPType_AddOp(old_value, value)
                    )

            elif c[0] == '{':
                self._rules.append((name.name(), BPType_Map.deserialize(io).evaluate(self._state)))
            else:
                raise BP_ParseError(io, "Invalid syntax")

        self._evaluated_variables = self._state.evaluate()
        

    def rules(self):
        return self._rules
    def variables(self):
        return self._evaluated_variables



                


