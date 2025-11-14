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



try:
    from . import blueprint
except ImportError:
    import blueprint


USAGE_PATTERNS_T = dict[str, dict[str, list[str]]]


class BlueprintNamespace:
    _usage_patterns: USAGE_PATTERNS_T
    _unknown_imports: set[str]

    def __init__(
        self, usage_patterns: USAGE_PATTERNS_T, unknown_imports: set[str]
    ) -> None:
        self._usage_patterns = usage_patterns
        self._unknown_importorts = unknown_imports

        


    def to_json(self):
        return {
            "usage_patterns": self._usage_patterns,
            "unknown_imports": list(self._unknown_imports)
        }
    @classmethod
    def from_json(cls, json_obj : dict) -> 'BlueprintNamespace':
        return cls(
            json_obj["usage_patterns"],
            json_obj["unknown_imports"]
        )


    def merge_from(self, other : 'BlueprintNamespace'):
        my_keys = set(self._usage_patterns.keys())
        other_keys = set(other._usage_patterns.keys())


        if len(intr := my_keys.intersection(other_keys)):
            raise ValueError("Duplicate keys detected!:", intr)

        self._unknown_imports -= other_keys
        self._usage_patterns = {**self._usage_patterns, **other._usage_patterns}
    
