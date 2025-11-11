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


import subprocess
from tempfile import TemporaryDirectory
from subprocess import check_output, check_call, DEVNULL


from os.path import dirname, abspath, join
import sys

sys.path.append(join(dirname(dirname(abspath(__file__))), "git-repo"))


from manifest_xml import XmlManifest, _XmlRemote, Project
from project import logger
logger.disabled = True




ANDROID_MANIFEST_URL = "https://android.googlesource.com/platform/manifest"

# An evil hack to fix a bug
# Note; This will break ALL other repos with a manifest!
_XmlRemote._resolveFetchUrl = lambda _: "https://android.googlesource.com/" 


def get_tags_for_repo(url: str) -> dict[str, str]:
    out = subprocess.check_output(["git", "ls-remote", url]).decode("utf-8").split("\n")
    return {x.split("\t")[1]: x.split("\t")[0] for x in out if x}


def get_cleaned_tags_for_repo(url: str) -> set[str]:
    return {
        k.replace("^{}", "").replace("refs/tags/", "")
        for k, v in get_tags_for_repo(url).items()
        if k.startswith("refs/tags/android-") and k.endswith("^{}")
    }


def get_manifest_tags() -> set[str]:
    return get_cleaned_tags_for_repo(ANDROID_MANIFEST_URL)


def get_file_tree(url: str, branch: str) -> list[str]:
    with TemporaryDirectory() as td:
        check_call(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--depth=1",
                "--branch",
                branch,
                url,
                ".",
            ],
            cwd=td,
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
        out = check_output(["git", "ls-tree", "-r", "HEAD", "--name-only"], cwd=td)
        return out.rstrip().decode("utf-8").split("\n")

def get_manifest_for(branch: str):
    with TemporaryDirectory() as td:
        check_output(["git", "clone", "--branch", branch, "--single-branch", ANDROID_MANIFEST_URL,  "--depth", "1"], cwd=td, stderr=DEVNULL)
        xmlPath = join(td, "manifest", "default.xml")
        manifest = XmlManifest(td, xmlPath)

        with open(xmlPath, "r") as f:
            cont = f.read()


        return [
            {"path": p.relpath, "url": p.remote.url, "revision" : p.revisionExpr}
            for p in manifest.projects
        ], cont











# android-14.0.0_r30
# print(get_cleaned_tags_for_repo("https://android.googlesource.com/platform/manifest"))
# print(get_cleaned_tags_for_repo("https://android.googlesource.com/platform/system/vold"))
