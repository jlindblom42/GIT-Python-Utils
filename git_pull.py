from git_base import change_dir_to_project, get_current_branch, init, print_successful_and_failed, projects, pull_branch

if not init('GIT Pull'):
    exit(1)

continue_answer = input("Do you want to continue? (Y/N) ").strip().upper()
if continue_answer != 'Y':
    exit(0)

print('-----------------')

successful = []
failed = []

for project in projects:
    change_dir_to_project(project)

    if not pull_branch(get_current_branch()):
        failed.append(project)
    else:
        successful.append(project)

print_successful_and_failed(successful, failed)
