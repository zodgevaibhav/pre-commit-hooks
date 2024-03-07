#!/usr/bin/env python

import os
import re
import sys
import argparse
import subprocess
from pre_commit_scripts.common.commit_scope_builder_module import  ConventionalCommitBuilder
from pre_commit_scripts.common.commit_scope_builder_module import  (Colors,RESULT_SUCCESS, RESULT_FAIL, valid_types)


class ConventionalPreCommit:

    def __init__(self, commit_msg_path):
        self.commit_msg_path = commit_msg_path

        self.optional_scope = True
        self.strict_mode = False

        self.subject = ""
        self.scope = ""
        self.body = ""
        self.commit_type = ""

        self.load_commit_message()
        self.parse_commit_message()
        self.check_commit_message_according_to_convention()
        self.check_commit_scope_comply_with_files_changed()
        if self.commit_type in ["fix", "revert"]:
            self.fix_revert_type_have_broken_commit_shas()

    def exit_with_error(self, message, description):
        print(f""" {Colors.LRED}\n[{message}]\n {Colors.RESTORE} "{description}" """)
        sys.exit(RESULT_FAIL)

    def load_commit_message(self):
        try:
            with open(self.commit_msg_path, encoding="utf-8") as f:
                self.commit_message = f.read()

        except UnicodeDecodeError:
            self.exit_with_error(
                "Bad Commit message encoding",
                f"""
                Conventional-pre-commit couldn't decode your commit message.
                UTF-8 encoding is assumed, please configure git to write commit messages in UTF-8.
                See https://git-scm.com/docs/git-commit/#_discussion for more.
                """,
            )

    def parse_commit_message(self):
        regex_pattern = self.commit_regex()
        match = re.match(regex_pattern, self.commit_message, re.MULTILINE)
        if match:
            self.commit_type = match.group("type")
            self.scope = match.group("scope")
            self.subject = match.group("subject")
            self.body = match.group("multi")
        else:
            self.exit_with_error(
                "Bad commit message",
                f"Commit message does not match conventions, commit message is :\n{self.commit_message}",
            )

    def commit_regex(self):
        all_types = "|".join(valid_types)
        types_pattern = rf"(?P<type>{all_types})"
        scope_pattern = self.r_scope(self.optional_scope)
        delim_pattern = self.r_delim()
        subject_pattern = self.r_subject()
        body_pattern = self.r_body()

        regex_pattern = rf"^{types_pattern}{scope_pattern}{delim_pattern}{subject_pattern}{body_pattern}"
        return regex_pattern

    def r_scope(self, optional=True):
        return r"(\((?P<scope>[\w \/:-]+)\))?" if optional else r"(\((?P<scope>[\w \/:-]+)\))"

    def r_delim(self):
        return r"!?:"

    def r_subject(self):
        return r"(?P<subject>.+)$"

    def r_body(self):
        return r"(?P<multi>(\r?\n(?P<sep>^$\r?\n)?.+)+)?"

    def check_commit_message_according_to_convention(self):
        errors = []

        if len(self.subject) > 50:
            errors.append("Subject line exceeds 50 characters")

        try:
            if not self.subject.strip()[0].isupper():
                errors.append("Subject line must start with a capital letter")
        except IndexError:
            self.exit_with_error("IndexError: Commit message conventions not followed", "Subject line is empty or too short")
        except Exception as ex:
            self.exit_with_error(f"Exception: Commit message conventions not followed - {type(ex).__name__}", str(ex))

        if self.subject.endswith("."):
            errors.append("Subject line must not end with a period")

        if type(self.body)==type(None):
                errors.append("Body seems empty, commit must have body")
        else:
            lines = self.body.split("\n")
            subjectLineCount=0
            for line in lines:
                if not line.strip().startswith("#"):
                    subjectLineCount=subjectLineCount+1

            if subjectLineCount<4:
                errors.append("Body line should be atleast of 2 line")   

            for line in lines:
                if not line.strip().startswith("#") and len(line) > 72:
                    errors.append("Body line exceeds 72 characters"+str(subjectLineCount))

        if errors:
            self.exit_with_error("Commit message conventions not followed", "\n".join(errors))

    def check_commit_scope_comply_with_files_changed(self):
        scopes  = ConventionalCommitBuilder().valid_scopes()

        if  self.scope is None or (self.scope and self.scope in scopes):
            sys.exit(0)
        else:
            self.exit_with_error(
                "Scope does not comply with files changed",
                f"Either give a valid scope or keep the scope empty.\nValid commit scopes: {str(scopes)} & provided commit scope is {str(self.scope)}",
            )

    def fix_revert_type_have_broken_commit_shas(self):
        def is_valid_commit_sha(sha):
            try:
                subprocess.check_output(
                    ["git", "rev-parse", "--verify", sha], stderr=subprocess.DEVNULL
                )
                return True
            except subprocess.CalledProcessError:
                return False

        sha_pattern = r"\b[0-9a-f]{7,40}\b"
        sha_list = re.findall(sha_pattern, self.body)
        if not sha_list:
            self.exit_with_error(
                "Commit Type Fix/Revert: Broken sha required",
                "For commit type fix & revert broken sha(s) must mention in commit body",
            )

        invalid_sha_list = [sha for sha in sha_list if not is_valid_commit_sha(sha)]
        if invalid_sha_list:
            self.exit_with_error(
                "Commit Type Fix: Invalid Sha",
                f"Invalid sha found in commit body.\nList of invalid sha : {str(invalid_sha_list)}",
            )

def main():
    parser = argparse.ArgumentParser(
        prog="conventional-pre-commit",
        description="Check a git commit message for Conventional Commits formatting.",
    )
    parser.add_argument(
        "input", type=str, help="A file containing a git commit message"
    )
    parser.add_argument(
        "--force-scope",
        action="store_false",
        default=True,
        dest="optional_scope",
        help="Force commit to have scope defined.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Force commit to strictly follow Conventional Commits formatting. Disallows fixup! style commits.",
    )

    args = parser.parse_args()
    ConventionalPreCommit(args.input)

if __name__ == "__main__":
    sys.exit(main())