from src.android_repo_searcher import *
from os.path import *

DEBUG_TAG = "android-11.0.0_r11"

base_test = join(dirname(dirname(abspath(__file__))), "base")

"""
clone_sparsly_filtered_repo_into(
    "https://android.googlesource.com/platform/frameworks/base",
    base_test,
    "bp"

)
"""

# set_git_branch(DEBUG_TAG, base_test)


