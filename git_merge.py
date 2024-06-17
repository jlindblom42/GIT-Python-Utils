from git_base import amend_commit, change_dir_to_project, count_uncommitted_changes, count_unpulled_commits, \
    count_unpushed_commits, fetch_and_checkout_and_pull_branch, get_first_artifact_version, \
    has_no_changes_in_working_directory, has_no_commits_to_push, init, merge_source_branch_to_destination_branch, \
    print_successful_and_failed, projects, skipversion, stage_all_changes, update_artifact_versions

if not init('GIT Merge'):
    exit(1)

if not skipversion:
    print('HINT: Provide "--skipversion" as an argument to skip POM version updates. ')
    print('')
else:
    print('[--skipversion Detected]: Will skip POM version updates.')
    print('')

for project in projects:
    change_dir_to_project(project, True)

    if count_uncommitted_changes():
        print(f'ERROR: Changes detected in working directory for project: "{project}"')
        print('Stash or revert changes and try again.')
        exit(0)

    if count_unpushed_commits():
        print(f'ERROR: Unpushed commits detected in current branch for project: "{project}"')
        print('Clean up current branch and try again.')
        exit(0)

    if count_unpulled_commits():
        print(f'ERROR: Unpulled commits detected in current branch for project: "{project}"')
        print('Clean up current branch and try again.')
        exit(0)

continue_answer = input("Do you want to continue? (Y/N) ").strip().upper()
if continue_answer != 'Y':
    exit(0)

print('-----------------')

deployment_ticket = input("Enter Deployment Ticket (e.g. DEV-1234): ").strip()
source_branch = input("Enter Source Branch: ").strip()
destination_branch = input("Enter Destination Branch: ").strip()

successful = []
failed = []

for project in projects:
    change_dir_to_project(project)

    if not has_no_changes_in_working_directory():
        failed.append(project)
        continue

    if not has_no_commits_to_push(source_branch):
        failed.append(project)
        continue

    if not has_no_commits_to_push(destination_branch):
        failed.append(project)
        continue

if len(failed):
    print(
        f'ERROR: The following projects had uncommitted changes or unpushed commits in "{source_branch}" and/or "{destination_branch}".')
    print('-----------------')
    print('\n'.join(failed))
    print('-----------------')
    print('Clean up projects with errors and try again.')
    exit(0)

for project in projects:
    change_dir_to_project(project)

    if not fetch_and_checkout_and_pull_branch(source_branch):
        failed.append(project)
        continue

    if not fetch_and_checkout_and_pull_branch(destination_branch):
        failed.append(project)
        continue

    if not merge_source_branch_to_destination_branch(source_branch, destination_branch):
        failed.append(project)
        continue

    if not skipversion:
        if not update_artifact_versions(project):
            failed.append(project)
            continue

        if not stage_all_changes():
            failed.append(project)
            continue

    version = get_first_artifact_version(project)
    commit_message = F"{deployment_ticket} Merge '{source_branch}' to '{destination_branch}' ({version})"

    if not amend_commit(commit_message):
        failed.append(project)
        continue

    successful.append(project)

print_successful_and_failed(successful, failed)
