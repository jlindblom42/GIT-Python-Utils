import argparse
import os
import re
import subprocess
from datetime import datetime
from xml.etree import ElementTree

from prettytable import PrettyTable

from git_projects import projects, projects_dir

BASE_GIT_CMD = [
    'git',
    '-c', 'diff.mnemonicprefix=false',
    '-c', 'core.quotepath=false',
    '--no-optional-locks'
]

parser = argparse.ArgumentParser(description='Configuration parameters.')
parser.add_argument('--poms', action='store_true', help='Include to output POM file locations.')
parser.add_argument('--skipversion', action='store_true', help='Skip the version update step of a script.')
parser.add_argument('--unpulled', action='store_true', help='Count the number of unpulled commits.')
args = parser.parse_args()
output_poms = args.poms
skipversion = args.skipversion
unpulled = args.unpulled


def is_git_installed():
    try:
        subprocess.check_output(["git", "--version"])
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def init(script_name, list_projects=True):
    print('-----------------')
    print(script_name)
    print('-----------------')

    validation_success = True

    if not is_git_installed():
        print(f'ERROR: "git" is not installed or accessible from command line.')
        validation_success = False

    if not os.path.isdir(projects_dir):
        print(f'ERROR: Not a valid directory: projects_dir=\"{projects_dir}\"')
        validation_success = False

    if list_projects:
        if not projects or len(projects) < 1:
            print(f'ERROR: No projects specified: projects=\"{projects}\"')
            print('Run "python git_find_projects.py" to get initial list and update "git_projects.py" with that list.')
            validation_success = False
        else:
            for project in projects:
                project_dir = get_project_dir(project)
                if not os.path.isdir(project_dir):
                    print(f'ERROR: Directory does not exist: {project_dir}')
                    validation_success = False
                elif not os.path.isdir(os.path.join(project_dir, '.git')):
                    print(f'ERROR: Directory does not contain a ".git" folder: {project_dir}')
                    validation_success = False

    if validation_success:
        if list_projects:
            print_version_status()
    else:
        print('Validation failed. Fix validation errors and try again.')

    return validation_success


def strip_project_dir(repo_dir):
    return repo_dir.replace(projects_dir + '\\', '').replace(projects_dir + '/', '').replace(projects_dir, '')


def change_dir_to_project(project, quiet=False):
    project_dir = get_project_dir(project)
    if not quiet:
        print('-----------------')
        print(project_dir)
        print('-----------------')
    os.chdir(project_dir)


def get_project_dir(project):
    # Split the input path by either forward slash (/) or backslash (\)
    project_parts = re.split(r'[\\/]+', project)

    # Use os.path.join to safely construct the path
    return os.path.join(projects_dir, *project_parts)


def get_current_branch():
    git_command = [
        'git',
        'rev-parse',
        '--abbrev-ref',
        'HEAD']
    return subprocess.check_output(git_command).decode('utf-8').strip()


def get_latest_commit_date():
    git_command = BASE_GIT_CMD + ['log', '-1', '--format=%cd', '--date=local']
    commit_date_str = subprocess.check_output(git_command).decode('utf-8').strip()
    commit_date = datetime.strptime(commit_date_str, "%a %b %d %H:%M:%S %Y")
    current_date = datetime.now()
    days_since_commit = (current_date - commit_date).days
    formatted_date = commit_date.strftime("%Y-%m-%d %I:%M %p")
    formatted_date = '%s (-%dd)' % (formatted_date, days_since_commit)
    return formatted_date


def print_version_status(exclude_hints_and_notes=False):
    table = PrettyTable()
    fields = [
        "Artifact Id",
        "Version",
        "Uncomm'd",
        "Unpushed"]

    if unpulled:
        fields += ["Unpulled"]

    fields += [
        "Branch",
        "Latest Commit"]

    if output_poms:
        fields.append("POM")

    table.field_names = fields
    table.align = "l"

    project_index = 1
    num_projects = len(projects)

    for project in projects:
        print(f'[{project_index}/{num_projects}] Retrieving meta for "{project}"')
        project_index += 1
        change_dir_to_project(project, quiet=True)
        project_git_meta = get_project_git_meta(project)

        index = 0

        for (artifact_id,
             artifact_version,
             num_committed_changes,
             num_unpushed_commits,
             num_unpulled_commits,
             current_branch,
             latest_commit_date,
             pom) in project_git_meta:

            index += 1

            divider = not index < len(project_git_meta)

            if not index == 1:
                latest_commit_date = ''
                current_branch = ''

            row = [
                artifact_id,
                artifact_version,
                num_committed_changes,
                num_unpushed_commits]

            if unpulled:
                row += [num_unpulled_commits]

            row += [
                current_branch,
                latest_commit_date]

            if output_poms:
                row.append(pom)

            table.add_row(row, divider=divider)

    print(table)

    if not exclude_hints_and_notes:
        if not output_poms:
            print('HINT: Provide "--poms" as an argument to print the POM directories. ')

        if not unpulled:
            print('HINT: Provide "--unpulled" as an argument to print the number of unpulled commits. (Note: very slow, ~4s per project)')

        print('NOTE: If script exits prematurely, run from terminal or try having "Run with Python Console" checked in run config.')

    print('')


def fetch_branch(branch):
    try:
        print(f"-- Fetch '{branch}'")
        git_command = BASE_GIT_CMD + ['fetch', '--no-tags', 'origin', f'{branch}:{branch}']
        print(' '.join(git_command))
        output = subprocess.check_output(git_command).decode('utf-8').strip()
        return "fatal" not in output

    except subprocess.CalledProcessError:
        print(f"ERROR: Unable to fetch '{branch}'")
        return False


def count_unpulled_commits(branch=get_current_branch()):
    try:
        # Fetch updates from the remote repository
        git_fetch_command = BASE_GIT_CMD + ['fetch']
        subprocess.run(git_fetch_command, check=True)

        # Get the number of unpulled commits
        git_count_command = BASE_GIT_CMD + ['rev-list', '--count', f'{branch}..origin/{branch}']
        unpulled_commits = subprocess.check_output(git_count_command, text=True).strip()

        return unpulled_commits
    except Exception as e:
        print(f"ERROR: {e}")
        return "ERR"


def count_uncommitted_changes():
    try:
        # Get the list of uncommitted changes
        git_command = BASE_GIT_CMD + ['status', '--porcelain']
        result = subprocess.run(git_command, capture_output=True, text=True)

        # Check for errors
        if result.returncode != 0:
            print("Error running git status.")
            return "ERR"

        # Split the output into lines
        changes = result.stdout.splitlines()

        # Count the number of changes
        num_changes = len(changes)

        return num_changes
    except Exception as e:
        print(f"ERROR: {e}")
        return "ERR"


def count_unpushed_commits():
    try:
        # Get the list of unpushed commits
        git_command = BASE_GIT_CMD + ['log', '--oneline', '@{u}..HEAD']
        result = subprocess.run(git_command, capture_output=True, text=True)

        # Check for errors
        if result.returncode != 0:
            print("Error running git log. Make sure your branch is tracking a remote branch.")
            return "ERR"

        # Split the output into lines
        commits = result.stdout.splitlines()

        # Count the number of commits
        num_commits = len(commits)

        return num_commits

    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e}")
        return "ERR"


def has_no_changes_in_working_directory():
    try:
        print(f"-- Check for changes in working directory")

        git_command = BASE_GIT_CMD + ['status', '--porcelain']
        print(' '.join(git_command))
        output = subprocess.run(git_command, stdout=subprocess.PIPE, text=True).stdout.strip()

        if output:
            print(output)
            print("-----------------")
            print("ERROR: Changes detected in working directory, stash or revert changes and try again.")
            return False

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def has_no_commits_to_push(branch):
    try:
        print(f"-- Check for unpushed commits for '{branch}'")

        git_command = BASE_GIT_CMD + ['rev-list', '--right-only', '--count', f"origin/{branch}...{branch}"]
        print(' '.join(git_command))
        result = subprocess.run(git_command, stdout=subprocess.PIPE, text=True).stdout.strip()

        count = int(result)

        if count > 0:
            print(f"There are {count} commits waiting to be pushed to origin/{branch}. Clean up branch and try again.")
            return False

        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def checkout_branch(branch):
    try:
        print(f"-- Checkout '{branch}'")
        git_command_checkout = BASE_GIT_CMD + ['checkout', branch, '--progress']
        print(' '.join(git_command_checkout))
        output = subprocess.check_output(git_command_checkout).decode('utf-8').strip()
        if "fatal" in output:
            print(f"ERROR: Unable to checkout '{branch}'")
            return False

        # Check if the upstream is already set
        git_command_rev_parse = BASE_GIT_CMD + ['rev-parse', '--abbrev-ref', branch + '@{u}']
        print(' '.join(git_command_rev_parse))
        result = subprocess.run(git_command_rev_parse, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"'{branch}' is tracking '{result.stdout.strip()}'")
            return True

        print(f"'{branch}' is not tracking a remote branch, updating to track 'origin/{branch}'")

        # Ensure the local branch tracks the origin branch
        git_command_set_upstream = BASE_GIT_CMD + ['branch', '--set-upstream-to=origin/' + branch, branch]
        print(' '.join(git_command_set_upstream))
        output = subprocess.check_output(git_command_set_upstream).decode('utf-8').strip()
        return "fatal" not in output

    except subprocess.CalledProcessError:
        print(f"ERROR: Unable to checkout '{branch}'")
        return False


def merge_source_branch_to_destination_branch(source_branch, destination_branch):
    try:
        print(f"-- Merge '{source_branch}' to '{destination_branch}'")
        git_command = BASE_GIT_CMD + ['merge', '--no-ff', source_branch]
        print(' '.join(git_command))
        output = subprocess.check_output(git_command).decode('utf-8').strip()

        return "fatal" not in output

    except subprocess.CalledProcessError:
        print(f"ERROR: Unable to merge '{source_branch}' to '{destination_branch}'")
        print('-- Attempting to resolve merge conflict')
        git_command = BASE_GIT_CMD + ['checkout', '--theirs', '.']
        print(' '.join(git_command))
        output = subprocess.check_output(git_command).decode('utf-8').strip()

        if "fatal" in output:
            return False

        git_command = BASE_GIT_CMD + ['add', '.']
        print(' '.join(git_command))
        output = subprocess.check_output(git_command).decode('utf-8').strip()

        if "fatal" in output:
            return False

        commit_msg = f'"Merged {source_branch} into {destination_branch} and resolved conflict with {source_branch} changes."'
        git_command = BASE_GIT_CMD + ['commit', '-m', commit_msg]
        print(' '.join(git_command))
        output = subprocess.check_output(git_command).decode('utf-8').strip()

        return "fatal" not in output


def amend_commit(commit_msg):
    try:
        print(f"-- Amend commit")
        git_command = BASE_GIT_CMD + ['commit', '-q', '--amend', '-m', commit_msg]
        print(' '.join(git_command))
        output = subprocess.check_output(git_command).decode('utf-8').strip()
        return "fatal" not in output

    except subprocess.CalledProcessError:
        print(f"ERROR: Unable stage pom.xml")
        return False


def stage_all_changes():
    try:
        print(f"-- Stage all changes")
        git_command = BASE_GIT_CMD + ['add', '.']
        print(' '.join(git_command))
        output = subprocess.check_output(git_command).decode('utf-8').strip()
        return "fatal" not in output

    except subprocess.CalledProcessError:
        print(f"ERROR: Unable stage pom.xml")
        return False


def pull_branch(branch):
    try:
        print(f"-- Pull '{branch}'")

        current_branch = get_current_branch()
        if current_branch != branch:
            print(f"ERROR: Pull branch '{branch}' != current branch '{current_branch}'.")
            return False

        if branch != 'dev' and branch != 'master':
            try:
                subprocess.run([
                    'git',
                    'ls-remote',
                    '--heads',
                    '--exit-code',
                    'origin',
                    f'refs/heads/{current_branch}'])

            except subprocess.CalledProcessError:
                print(f"ERROR: No origin in remote for '{branch}'")
                return False

        git_command = BASE_GIT_CMD + ['pull', '--rebase', 'origin', branch]
        print(' '.join(git_command))
        output = subprocess.check_output(git_command).decode('utf-8').strip()
        return "fatal" not in output

    except subprocess.CalledProcessError:
        print(f"ERROR: Unable to pull '{branch}'.")
        return False


def fetch_and_checkout_and_pull_branch(branch):
    print("-- Detecting current branch")
    current_branch = get_current_branch()

    if current_branch != branch:
        print(f"Current branch is '{current_branch}', performing checkout of '{branch}'.")

        if not fetch_branch(branch):
            return False

        if not checkout_branch(branch):
            return False

        current_branch = get_current_branch()

        if current_branch != branch:
            print(f"ERROR: Could not checkout '{branch}'.")
            return False

    else:
        print(f"Current branch is already '{branch}', skipping checkout.")
        return pull_branch(branch)

    return True


def find_pom_files(directory):
    pom_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file == "pom.xml":
                pom_files.append(os.path.join(root, file))
    return pom_files


def get_project_git_meta(project):
    # current_timestamp_seconds_initial = time.time()
    project_dir = get_project_dir(project)
    pom_files = find_pom_files(project_dir)
    num_uncomitted_changes = str(count_uncommitted_changes())
    num_unpushed_commits = str(count_unpushed_commits())
    current_branch = get_current_branch()

    num_unpulled_commits = ''
    if unpulled:
        num_unpulled_commits = str(count_unpulled_commits(current_branch))

    latest_commit_date = get_latest_commit_date()

    artifact_versions = []

    if not pom_files:
        pom_files = []

    if len(pom_files) < 1:
        print(f"WARN: No 'pom.xml' files found in project dir: '{project_dir}'")
        pom_files.append('')

    first = True
    for pom_file_path in pom_files:
        version_tag_text = 'N/A'
        artifact_id_text = None

        if pom_file_path != '':
            tree = ElementTree.parse(pom_file_path)
            root = tree.getroot()
            namespaces = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            version_tag = root.find('maven:version', namespaces)

            if version_tag is not None:
                version_tag_text = version_tag.text
            else:
                version_tag = root.find('maven:parent/maven:version', namespaces)

                if version_tag is not None:
                    version_tag_text = f"{version_tag.text} (p)"

            if version_tag_text is not None:
                artifact_id = root.find('maven:artifactId', namespaces)

                if not first:
                    nested = '-> '
                    current_branch = ''
                else:
                    nested = ''

                artifact_id_text = f"{nested}{artifact_id.text}"

        if artifact_id_text is None:
            artifact_id_text = project

        if not first:
            num_uncomitted_changes = ''
            num_unpushed_commits = ''
            num_unpulled_commits = ''
            current_branch = ''
        else:
            current_branch = current_branch if len(current_branch) <= 18 else current_branch[:18] + '...'

        if pom_file_path is not None:
            pom_file_path = strip_project_dir(pom_file_path)

        artifact_versions.append(
            (artifact_id_text,
             version_tag_text,
             num_uncomitted_changes,
             num_unpushed_commits,
             num_unpulled_commits,
             current_branch,
             latest_commit_date,
             pom_file_path))
        first = False

    # print(f'Done. [{round(time.time() - current_timestamp_seconds_initial, 2)}s]')
    return artifact_versions


def update_artifact_versions(project):
    print(f"-- Update artifact versions")
    current_branch = get_current_branch()
    project_dir = get_project_dir(project)
    pom_files = find_pom_files(project_dir)

    if not pom_files:
        pom_files = []

    if len(pom_files) < 1:
        print(f"WARN: No 'pom.xml' files found in project dir: '{project_dir}'")
        pom_files.append('')

    if current_branch == 'dev':
        for pom_file_path in pom_files:
            version_tag_text = None

            if pom_file_path != '':
                tree = ElementTree.parse(pom_file_path)
                root = tree.getroot()
                namespaces = {'maven': 'http://maven.apache.org/POM/4.0.0'}
                version_tag = root.find('maven:version', namespaces)

                if version_tag is not None:
                    version_tag_text = version_tag.text
                else:
                    version_tag = root.find('maven:parent/maven:version', namespaces)

                    if version_tag is not None:
                        version_tag_text = version_tag.text

            if version_tag_text is not None:
                pattern = version_tag_text.replace('.', '\\.')

                with open(pom_file_path, 'r') as file:
                    content = file.read()

                def update_version(x):
                    existing_version = x.group(0)
                    major, minor = map(int, existing_version.split('.'))
                    new_version = f"{major}.{minor + 1}-SNAPSHOT"
                    print(f'Replacing version "{existing_version}" with "{new_version}"')
                    return new_version

                modified_content = re.sub(pattern, update_version, content)

                with open(pom_file_path, 'w') as file:
                    file.write(modified_content)

    if current_branch == 'master':
        for pom_file_path in pom_files:
            print(f'Processing "{pom_file_path}"')
            if pom_file_path != '':
                with open(pom_file_path, 'r') as file:
                    content = file.read()

                def update_version(x):
                    existing_version = x.group(0)
                    new_version = existing_version.replace('-SNAPSHOT', '')
                    print(f'Replacing version "{existing_version}" with "{new_version}"')
                    return new_version

                pattern = r'\d+\.\d+-SNAPSHOT'
                modified_content = re.sub(pattern, update_version, content)

                with open(pom_file_path, 'w') as file:
                    file.write(modified_content)

    return True


def get_first_artifact_version(project):
    current_branch = get_current_branch()
    project_dir = get_project_dir(project)
    pom_files = find_pom_files(project_dir)

    if not pom_files:
        pom_files = []

    if len(pom_files) < 1:
        print(f"WARN: No 'pom.xml' files found in project dir: '{project_dir}'")
        pom_files.append('')

    for pom_file_path in pom_files:
        if pom_file_path != '':
            tree = ElementTree.parse(pom_file_path)
            root = tree.getroot()
            namespaces = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            version_tag = root.find('maven:version', namespaces)

            if version_tag is not None:
                return version_tag.text
            else:
                version_tag = root.find('maven:parent/maven:version', namespaces)

                if version_tag is not None:
                    return version_tag.text

    return "N/A"


def print_successful_and_failed(successful, failed):
    if successful and len(successful) > 0:
        print('-----------------')
        print('Successful')
        print('-----------------')
        print('\n'.join(successful))
    if failed and len(failed) > 0:
        print('-----------------')
        print('Failed')
        print('-----------------')
        print('\n'.join(failed))
    print('-----------------')
    print_version_status(exclude_hints_and_notes=True)
    print('DONE.')
