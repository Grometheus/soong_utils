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


from os import listdir, makedirs, walk
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


def clone_manifest_into(branch: str, tag_dir: str):
    check_call(
        [
            "git",
            "clone",
            "--depth=1",
            "--single-branch",
            "--branch",
            branch,
            ANDROID_MANIFEST_URL,
            ".",
        ],
        cwd=tag_dir,
        stdout=DEVNULL,
        stderr=DEVNULL,
    )


def is_typical_tag(tag_dir: str) -> bool:
    listing = listdir(tag_dir)
    return (
        sum((1 for f in listing if f.endswith(".xml"))) == 1
        and "default.xml" in listing
    )


def get_manifest_for(tag_dir: str):
    xmlPath = join(tag_dir, "default.xml")
    manifest = XmlManifest(tag_dir, xmlPath)

    return [
        {"path": p.relpath, "url": p.remote.url, "revision": p.revisionExpr}
        for p in manifest.projects
    ]


def clone_git_into(repo_url: str, out_dir: str):
    makedirs(out_dir)
    check_call(
        [
            "git",
            "clone",
            repo_url,
            ".",
        ],
        cwd=out_dir,
        stdout=DEVNULL,
        stderr=DEVNULL,
    )


def set_git_branch(branch: str, repo_dir: str):
    check_call(
        ["git", "checkout", branch], cwd=repo_dir, stdout=DEVNULL, stderr=DEVNULL
    )


def search_for_extensions(ext: str, repo_dir: str):
    out = []
    for dir_path, _, files in walk(repo_dir):
        out += [join(dir_path, fn) for fn in files if fn.endswith(ext)]
    return out


# android-14.0.0_r30
# print(get_cleaned_tags_for_repo("https://android.googlesource.com/platform/manifest"))
# print(get_cleaned_tags_for_repo("https://android.googlesource.com/platform/system/vold"))
