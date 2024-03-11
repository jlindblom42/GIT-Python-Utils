import subprocess

from git_base import init

if not init('GIT Enable Common Config', list_projects=False):
    exit(1)

# Check current Git configuration for pull.rebase and rebase.autoStash
try:
    pull_rebase_output = subprocess.check_output(
        ["git", "config", "--global", "--get", "pull.rebase"]).strip().decode()
except subprocess.CalledProcessError as e:
    pull_rebase_output = "false"

try:
    auto_stash_output = subprocess.check_output(
        ["git", "config", "--global", "--get", "rebase.autoStash"]).strip().decode()
except subprocess.CalledProcessError as e:
    auto_stash_output = "false"

try:
    if pull_rebase_output.lower() != "true":
        print('Setting "pull.rebase" to "true".')
        subprocess.check_call(["git", "config", "--global", "pull.rebase", "true"])
    else:
        print('"pull.rebase" already set to "true".')
except subprocess.CalledProcessError as e:
    print(f'ERROR: Was unable to enable git "pull.rebase".')

try:
    if auto_stash_output.lower() != "true":
        print('Setting "rebase.autoStash" to "true".')
        subprocess.check_call(["git", "config", "--global", "rebase.autoStash", "true"])
    else:
        print('"rebase.autoStash" already set to "true".')
except subprocess.CalledProcessError as e:
    print(f'ERROR: Was unable to enable git "pull.rebase".')
