#!/usr/bin/env python3

import os
import sys
from pre_commit_scripts.common.commit_scope_builder_module import  ConventionalCommitBuilder


def main():
    COMMIT_MSG_FILE = sys.argv[1]

    COMMIT_SOURCE = os.getenv("PRE_COMMIT_COMMIT_MSG_SOURCE", "message")

    if COMMIT_SOURCE == "message":
        ConventionalCommitBuilder().prepare_commit_message(COMMIT_MSG_FILE)


if __name__ == "__main__":
    main()