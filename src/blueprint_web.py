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
    
