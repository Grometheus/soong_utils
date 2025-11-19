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
    from .blueprint_parser import BlueprintFile, EVAL_VALUE
except ImportError:
    from blueprint_parser import BlueprintFile, EVAL_VALUE

import os
import pickle
import logging
from typing import cast

from blueprint_parser import BP_EvalError

FILE_REGISTRY_T = dict[str, list[tuple[str, EVAL_VALUE]]]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)




def merge_dict(dst : dict[str, EVAL_VALUE], src : dict[str, EVAL_VALUE]):
    for k in src.keys():

        # What cannot be inherited
        if k in ["name", "defaults", "visibility"]:
            continue
        # Simple case of a key not presant
        if not k in dst:
            dst[k] = src[k]
            continue


        if type(dst[k]) is not type(src[k]):
            logger.warn(f"Unable to merge dictionaries with values of different types. Key: {k}. Value from dst {dst[k]}. Value from src {src[k]}")
            continue

        # These types have a defined action for defaults
        if type(dst[k]) is dict:
            merge_dict(dst[k], src[k])
            continue
        if type(dst[k]) is list:
            dst[k] += src[k]
            continue

        # Otherwise just keep the original
        # (nothing needs done)
class BPE_SourceFile:
    def __init__(self, path : str, modules : list['BPE_Module'] | None = None) -> None:
        self.path = path
        self.modules = modules or []
    def register(self, module : 'BPE_Module'):
        self.modules.append(module)

class BPE_Module:
    def __init__(self, idx : int, rule : str, values : dict[str, EVAL_VALUE], source : BPE_SourceFile) -> None:
        self.idx = idx
        self.rule = rule
        self.values = values

        self.source = source

    def get_lookup_name(self) -> str:
        if self.rule.endswith("_defaults"):
            if not "name" in self.values:
                raise BP_EvalError(None, "Name MUST be defined for a `defaults` rule")

            return "@defaults/" + self.values["name"]
        # TODO: Are there more meta modules?

        if not "name" in self.values:
            return f"#{self.source.path}/{self.idx}" 
        return self.rule+"/"+self.values["name"] 
    def merge_defaults_from(self, other : 'BPE_Module'):
        merge_dict(self.values, other.values)







class BPE_BlueprintConsumer:


    # Note: objects SHOULD BE ALIASED BETWEEN DICTS
    _file_registry: dict[str, BPE_SourceFile] 
    _object_registry: dict[str, BPE_Module]


    def __init__(self) -> None:
        self._file_registry = {}
        self._object_registry = {}



    def to_file(self, path : str):
        with open(path, "wb") as f:
            pickle.dump(self.__dict__, f)


    @classmethod
    def from_file(cls, path : str) -> 'BPE_BlueprintConsumer':
        with open(path, "rb") as f:
            new_dict  = pickle.load(f)

        obj = cls()

        assert type(new_dict) is dict
        assert set(obj.__dict__.keys()) == set(new_dict.keys())

        obj.__dict__ = new_dict
        return obj





    def merge_from(self, other: "BPE_BlueprintConsumer"):
        my_keys = set(self._object_registry.keys())
        other_keys = set(other._object_registry.keys())

        if len(intr := my_keys.intersection(other_keys)):
            raise ValueError("Duplicate keys detected!:", intr)
        self._object_registry |= other._object_registry
        self._file_registry |= other._file_registry



    def injest(self, bp_file: str):
        """
        Takes in a .bp file, and adds it to the dependency info.
        """


        with open(bp_file, "r") as f:
            bpf = BlueprintFile.from_str(f.read(), True)

        sourceFile = BPE_SourceFile(os.path.abspath(bp_file))

        # Note: Creates aliases (But it doesn't matter)
        file_rules = bpf.rules()


        for i, (rule, values) in enumerate(file_rules):
            m = BPE_Module(i, rule, values, sourceFile)


            # Meta medules that determine the build system:
            # https://github.com/AOSP-15-Dev/android_build_soong/blob/677aa108ce2cb58f3392254dd04dd7925024c728/android/soong_config_modules.go#L40
            
            if rule in [
                "soong_config_module_type_import", 
                "soong_config_module_type", 
                "soong_config_string_variable", 
                "soong_config_bool_variable", 
                "soong_config_value_variable"]:
                # TODO: Figure out this
                continue
            name = m.get_lookup_name()
            if name in self._object_registry:
                raise BP_EvalError(None, f"Duplicate key '{name}' found!")
 
            self._object_registry[name] = m
            sourceFile.register(m)
        self._file_registry[sourceFile.path] = sourceFile 
    
    def compute_defaults(self):
        for name, obj in filter(lambda o: "defaults" in o[1].values, self._object_registry.items()):
            for default in obj.values["defaults"]:
                lookup = "@defaults/" + default
                if not lookup in self._object_registry:
                    logger.warning(f"Cannot resolve default {default} in {name}, skipping!")
                    continue
                obj.merge_defaults_from(self._object_registry[lookup])



    def debug(self):
        import json
        return json.dumps(self._object_registry, indent=2)



from android_repo_searcher import search_for_extensions

col = BPE_BlueprintConsumer()
for file in search_for_extensions(".bp", "/home/mitch/Documents/grom/base/"):
    col.injest(file)
col.compute_defaults()
print(col.debug())






