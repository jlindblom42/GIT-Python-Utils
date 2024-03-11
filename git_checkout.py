from git_base import change_dir_to_project, fetch_and_checkout_and_pull_branch, init, print_successful_and_failed, projects

if not init('GIT Checkout'):
    exit(1)

continue_answer = input("Do you want to continue? (Y/N) ").strip().upper()
if continue_answer != 'Y':
    exit(0)

print('-----------------')
destination_branch = input("Enter Destination Branch: ").strip()

successful = []
failed = []

for project in projects:
    change_dir_to_project(project)

    if not fetch_and_checkout_and_pull_branch(destination_branch):
        failed.append(project)
    else:
        successful.append(project)

print_successful_and_failed(successful, failed)
