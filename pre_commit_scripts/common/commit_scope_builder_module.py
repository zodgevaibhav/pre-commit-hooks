import os
import sys
import subprocess
from collections import Counter
import re

#--------------------------------------------------------------------
# Adjust the following as the repo evolves
#--------------------------------------------------------------------

# Define valid commit types
all_types = "build, ci, docs, feat, fix, perf, refactor, style, test, chore"
valid_types = [typ.strip() for typ in all_types.split(",")]

# List of top level directories that define scope. Sub-directories of these
# are considered part of this top. Add any such new top level directories here.

top_level_scope_dirs = ["src/main", ".github", ".pre-commit-scripts"]

# Name mapper that maps a directory name to a scope name. The directory can
# be any that is listed in top_level_scope_dirs or a sub-directory of a
# project root sub-directory. The mapping is to keep the scopes short

pre_commit_scope = "pre-commit"
dirs_scope_map = {
    ".github": "",
    ".pre-commit-scripts": pre_commit_scope,
    "src/main": "main",
}

# When there are multiple scopes in a commit, it usually is an indication
# of an atomic commit that updates a library and its usage(s). In such cases
# it makes more sense to have the scope narrow to the library. This is
# defined by a scope "yielding" to another as below:

scope_yields = {
  "services": "main"  # services yield to X in atomic commits
}

# Take care of typical scenario of committing tests and features in
# an atomic commit. Add others if needed

type_yields = {
  "test": "feat" # when there are tests and feats in same scope
}

# Repo main branch used for hints
#
main_branch = "main"
include_examples = 3 # Set to 0 if everyone is an expert

#--------------------------------------------------------------------
# End of adjustables
#--------------------------------------------------------------------

class Colors:
    LBLUE = "\033[00;34m"
    LRED = "\033[01;31m"
    RESTORE = "\033[0m"
    YELLOW = "\033[00;33m"


RESULT_SUCCESS = 0
RESULT_FAIL = 1

class ConventionalCommitBuilder:


    def __init__(self, root="."):
        self.root = root

    def hint(self):
        scopes = self.valid_scopes()
        all_scopes = ', '.join(scopes)

        examples = ''
        if include_examples > 0:
            commit_logs = subprocess.check_output(['git', 'log', '--oneline', '--format=%s', '-n', str(include_examples), main_branch], text=True)
            lines = [f'# {line}' for line in commit_logs.strip().split('\n')]
            all_examples = '\n'.join(lines)
            examples = f'''\
                # Some examples:
                #
                {all_examples}
                #'''

        hint = f'''

           # Please enter the commit message for your changes following
           # conventional commit guide-lines. Lines starting with '#' will
           # be ignored, and an empty message or a commit message that does
           # not comply with commit guidelines, aborts the commit.
           #
           # Valid conventional commit types:
           #  {all_types}
           #
           # Valid conventional commit scopes:
           #  {all_scopes}
           #
        '''

        return '\n'.join(map(str.lstrip, (hint + examples).split('\n')))


    def exit_with_error(self, message, description):
        print(f""" {Colors.LRED}\n[{message}]\n {Colors.RESTORE} "{description}""")
        sys.exit(RESULT_FAIL)

    def exit_with_warning(self, message, description):
        print(
            f""" {Colors.YELLOW}\n[{message}]\n {Colors.RESTORE} "{description}""",
            file=sys.stdout,
        )
        sys.exit(RESULT_SUCCESS)

    def get_staged_changes_file_list(self):  # Needed
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-status"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            staged_changes_status = result.stdout.splitlines()
            return staged_changes_status
        except subprocess.CalledProcessError as e:
            print(
                f"Error: Retrieving staged changes status\nError executing git command: {e}"
            )
            return []

    def to_scope_yield(self, s):
        return s if s not in scope_yields else scope_yields[s]

    def to_scope(self, d):
        return d if d not in dirs_scope_map else dirs_scope_map[d]

    def list_subdirectories(self, root_dir):

        # Check if the directory has any commits
        def has_commits(directory):
            path = os.path.join(root_dir, directory)
            commit_logs = subprocess.check_output(['git', 'log', '--oneline', '-n', '1', path], text=True)

            return len(commit_logs.strip().split('\n')[0]) > 0

        return [entry.name for entry in os.scandir(root_dir) if entry.is_dir() and has_commits(entry.name)]


    def valid_scopes(self):
        root = self.root
        ignored_dirs_for_scope = [".git", "project"]
        dirs = [
            d
            for d in self.list_subdirectories(root)
            if d not in top_level_scope_dirs
            and d not in ignored_dirs_for_scope
        ]
        subs = []
        for d in dirs:
            s = [
                s
                for s in self.list_subdirectories(os.path.join(root, d))
                if s not in ignored_dirs_for_scope
            ]
            subs.extend(s)
        subs.extend(top_level_scope_dirs)
        subs.extend(dirs)  # for collapsing in case of multiple sub-dir scopes

        scopes = set([self.to_scope(d) for d in subs])
        scopes.remove('')
        return sorted(scopes)

    def get_file_type(self, file_name):
        if file_name.startswith(".github"):
            return ("ci", "")
        if file_name.startswith(".pre-commit"):
            return ("build", pre_commit_scope)

        maven_files_regex = re.compile(r"pom.xml")
        sub_dir_regex = re.compile(r"^([^/]*)/([^/]+)/.*$")
        if maven_files_match := maven_files_regex.match(file_name):
            return ("build", self.to_scope(maven_files_match.group(1)))
        if sub_dir_match := sub_dir_regex.match(file_name):
            top, sub = (sub_dir_match.group(1), sub_dir_match.group(2))
            if top in top_level_scope_dirs:
                return ("feat", self.to_scope(top))
            return ("feat", self.to_scope(top) + "/" + self.to_scope(sub))
        return ("chore", "")

    def sort_by_occurance(self, tuple_list):
        tuple_counts = Counter(tuple_list)
        distinct_tuples = set(tuple_list)
        # Create a sorted list with distinct items and their counts
        return sorted(
            [(item, tuple_counts[item]) for item in distinct_tuples],
            key=lambda x: x[1],
            reverse=True,
        )

    def get_commit_type(self, files):
        types = [self.get_file_type(f) for f in files]
        sorts = self.sort_by_occurance(types)
        if len(sorts) > 1:
            # collapse sub-trees to parent
            types = [(typ, scope.split("/")[0]) for (typ, scope) in types]
            sorts = self.sort_by_occurance(types)
        if len(sorts) > 1:
            # collapse with yields
            types = [(typ, self.to_scope_yield(scope)) for (typ, scope) in types]
            sorts = self.sort_by_occurance(types)
        if len(sorts) == 1:
            t, c = sorts[0]
            typ, scope = t
            if len(scope.split("/")) == 2:
                scope = scope.split("/")[1]
            return (typ, scope)
        return ("chore", "")

    def get_all_changed_files(self, staged_changes_file_list):
        modified_files = [
            line.split("\t")[-1]
            for line in staged_changes_file_list
            if line.startswith("M\t")
        ]
        self.new_files_added = [
            line.split("\t")[-1]
            for line in staged_changes_file_list
            if line.startswith("A\t")
        ]
        return modified_files + self.new_files_added

    def derive_commit_type_scope(self):
        lines = self.get_staged_changes_file_list()
        files = self.get_all_changed_files(lines)
        return self.get_commit_type(files)

    def prepare_commit_message(self, commit_msg_file):
        typ, scope = self.derive_commit_type_scope()
        suggestion = typ if scope == "" else f"{typ}({scope})"
        hint = self.hint()

        with open(commit_msg_file, "r") as file:
            lines = file.readlines()

        for line in lines:
            if line.strip() != '' and not line.startswith('#'):
                return # Do nothing

        with open(commit_msg_file, "w") as file:
            file.write(suggestion + ": ")
            file.write(hint)

            # Write everything except the hint from original
            writing = True
            for line in lines:
                if re.match(r'^. Please enter the commit message', line):
                    writing = False
                    continue
                elif re.match(r'^#$', line):
                    writing = True
                    continue

                if writing:
                    file.write(line)