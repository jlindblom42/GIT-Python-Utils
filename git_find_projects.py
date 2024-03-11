import os

from git_base import init, projects_dir, strip_project_dir

if not init('GIT Find Projects', list_projects=False):
    exit(1)

repos = []
for root, dirs, files in os.walk(projects_dir):
    if '.git' in dirs:
        repos.append(root)
        dirs[:] = []
    else:
        for subdir in dirs:
            for subroot, subdirs, subfiles in os.walk(subdir):
                if '.git' in subdirs:
                    repos.append(subroot)
                    # Prevents diving deeper into subdirectories once .git is found
                    subdirs[:] = []
                    dirs[:] = []

for repo in repos:
    repo_dir = strip_project_dir(repo)
    repo_dir = repo_dir.replace('\\', '\\\\')
    print(f"'{repo_dir}',")
