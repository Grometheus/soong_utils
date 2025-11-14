#!/usr/bin/env python3

from os import makedirs
from os.path import *
import time
import traceback
import sys
from subprocess import SubprocessError, check_call

from src.event_system import *
from src.android_repo_searcher import *
from shutil import rmtree

DEBUG = False 

DEBUG_TAG = "android-11.0.0_r22"


# Get all the valid android version manifest tags
# Note: not cached
class AndroidManifestTagsEvent(Event[list[str]]):
    @classmethod
    def run(cls, ctrl: EventCtrl, out_dir : str) -> list[str]:
        tags = list(sorted(get_manifest_tags()))

        print("Debug mode, overwriding tags!")
        if DEBUG:
            tags = [DEBUG_TAG]

        with open(join(out_dir, "manifest_tags.json"), "w", encoding="utf-8") as f:
            json.dump(tags, f, indent=2)

        return tags



class CloneManifestByTag(Event[str]):
    def __init__(self, *args) -> None:
        self.tag_dir = args[0]

        super().__init__(*args)

    def can_easily_fufill(self) -> bool:
        return exists(self.tag_dir)
    def easily_fufill(self, ctrl: EventCtrl):
        return self.tag_dir



    @classmethod
    def run(cls, ctrl: EventCtrl, tag_dir : str, tag : str) -> str:
        makedirs(tag_dir, exist_ok=False)
        
        for _ in range(64):
            try:
                clone_manifest_into(tag, tag_dir)
                break
            except SubprocessError:
                pass
        else:
            raise Exception(f"Cannot clone manifest for {tag}, retries exceeded")

        rmtree(join(tag_dir, ".git"))

        return tag_dir


class ExtractTagsInBulk(Event[None]):
    @classmethod
    def run(cls, ctrl: EventCtrl, out_dir : str, *tag_dirs):
        all_projects = set()
        project_by_tag = {}



        for tag_dir in tag_dirs:
            tag = basename(tag_dir)
            if not is_typical_tag(tag_dir):
                print(f"Warning: {tag} does not seem typical, skipping!")
                continue
            
            projects = get_manifest_for(tag_dir)
            project_by_tag[tag] = projects

            all_projects.update(map(json.dumps, projects))

        # At this point this all is too large to keep in ram for much longer.
        path = join(out_dir, "manifest_projects.json.gz")
        with gzip.open(path, "wt") as f:
            json.dump({
                "projects_by_tag": project_by_tag,
                "all_projects": [json.loads(p) for p in all_projects],
                    }, f, indent=2
                )
        return path
                     




class TagSearcherEvent(Event[None]):
    @classmethod
    def run(cls, ctrl: EventCtrl, out_dir : str, tags : list[str]):


        manifest_resolvers = [
            CloneManifestByTag(join(out_dir, "manifests", tag), tag)
            for tag in tags
        ]
        
        ctrl.enqueue_event(ExtractTagsInBulk(out_dir, *manifest_resolvers))



def output_to(out_dir: str) -> None:
    with EventManager(max_workers=32, do_log=True) as mng:
        tags_e = AndroidManifestTagsEvent(out_dir)


        mng.schedule_event(TagSearcherEvent(out_dir, tags_e))


        # Demo: second run should still print because dependency resolves


        # Example for later:
        # tags = sorted_manifest_tags()
        # with open(join(out_dir, "manifest_tags.json"), "w", encoding="utf-8") as f:
        #     json.dump(tags, f, indent=2, ensure_ascii=False)
        # for tag in tags:
        #     mng.enqueue_event(AndroidVersionEvent(out_dir, tag))


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: collect_data.py OUTPUT_DIR")
        sys.exit(1)

    output = abspath(sys.argv[1])
    if not exists(output) or not isdir(output):
        print("Error: OUTPUT_DIR must be an existing directory")
        sys.exit(1)

    output_to(output)


if __name__ == "__main__":
    main()
