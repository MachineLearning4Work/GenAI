# Connect a New Project to GitHub Using a New Branch

This guide shows how to take an existing project, initialize Git, create a new branch, connect it to GitHub, and upload the project without overwriting the repository's existing `main` branch.

The example project is:

```text
C:\....\terraform-terragrunt-ml-demo
```

The example GitHub repository is:

```text
https://github.com/MachineLearning4Work/GenAI.git
```

The example branch name is `mlops-demo`. You can replace this name with any branch name you prefer.

## 1. Open PowerShell in the project directory

Navigate to the folder containing your code:

```powershell
cd "C:\Docs\Mehdi\Teaching\MLOps\python_code\terraform-terragrunt-ml-demo"
```

You can confirm that the project files are present with:

```powershell
Get-ChildItem
```

## 2. Check whether the folder is already a Git repository

Run:

```powershell
git status
```

If Git responds with:

```text
fatal: not a git repository (or any of the parent directories): .git
```

initialize Git in the current folder:

```powershell
git init
```

This creates a hidden `.git` directory and turns the project folder into a local Git repository.

> Run `git init` only in the project's root directory. Do not run it inside a subfolder such as `data` or `infra` unless you intentionally want a separate repository.

## 3. Create and switch to a new branch

Create a new branch for the project and switch to it:

```powershell
git switch -c mlops-demo
```

To verify the current branch:

```powershell
git branch --show-current
```

Expected output:

```text
mlops-demo
```

The older equivalent command is:

```powershell
git checkout -b mlops-demo
```

## 4. Review untracked files

Check the repository status:

```powershell
git status
```

New project files may appear under `Untracked files`, for example:

```text
.dockerignore
.gitignore
Dockerfile.tools
README.md
README.txt
data/
docker-compose.yml
infra/
ml_job.py
run.sh
```

Before adding files, check that `.gitignore` excludes files that should not be committed, such as passwords, API keys, virtual environments, generated files, and local Terraform state.

A useful `.gitignore` may include:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Secrets and local environment files
.env
.env.*
!.env.example

# Terraform
.terraform/
*.tfstate
*.tfstate.*
.terraform.lock.hcl

# Operating-system files
.DS_Store
Thumbs.db
```

Review the files that will be staged:

```powershell
git status --short
```

## 5. Add all project files to the new branch

Stage all files in the project:

```powershell
git add .
```

Review the staged files before committing:

```powershell
git status
```

To inspect the exact staged changes:

```powershell
git diff --cached
```

If a secret or unwanted file was staged accidentally, remove it from staging without deleting the local file:

```powershell
git restore --staged path\to\file
```

## 6. Create the first commit

Commit the staged project files:

```powershell
git commit -m "Add Terraform Terragrunt MLOps demo"
```

Confirm that the working tree is clean:

```powershell
git status
```

A clean repository normally reports:

```text
nothing to commit, working tree clean
```

## 7. Connect the local repository to GitHub

Add the GitHub repository as the remote named `origin`:

```powershell
git remote add origin https://github.com/MachineLearning4Work/GenAI.git
```

Verify the remote:

```powershell
git remote -v
```

Expected output resembles:

```text
origin  https://github.com/MachineLearning4Work/GenAI.git (fetch)
origin  https://github.com/MachineLearning4Work/GenAI.git (push)
```

If Git reports that `origin` already exists, update its URL instead:

```powershell
git remote set-url origin https://github.com/MachineLearning4Work/GenAI.git
```

## 8. Push the new branch to GitHub

Upload the local branch and set its upstream branch:

```powershell
git push -u origin mlops-demo
```

The `-u` option connects the local `mlops-demo` branch to the remote branch. After this first push, future updates can usually be uploaded with simply:

```powershell
git push
```

Depending on your GitHub account configuration, Git may ask you to authenticate. Use GitHub Desktop, Git Credential Manager, a personal access token, or SSH authentication. GitHub no longer accepts a normal account password for HTTPS Git operations.

## 9. Verify the branch on GitHub

Open:

```text
https://github.com/MachineLearning4Work/GenAI/tree/mlops-demo
```

You should see the project files on the `mlops-demo` branch.

You can also verify locally:

```powershell
git branch -vv
git status
```

## Complete command sequence

For a new local repository, the complete sequence is:

```powershell
cd "C:\...\terraform-terragrunt-ml-demo"

git init
git switch -c mlops-demo
git add .
git commit -m "Add Terraform Terragrunt MLOps demo"
git remote add origin https://github.com/MachineLearning4Work/GenAI.git
git push -u origin mlops-demo
```

## If `origin` already exists

Use this version instead of `git remote add origin`:

```powershell
git remote set-url origin https://github.com/MachineLearning4Work/GenAI.git
git push -u origin mlops-demo
```

## If the GitHub repository already contains files

If the remote repository already has a `README.md`, license, or other commit, the first push may be rejected because the local and remote histories are unrelated. First download the remote history:

```powershell
git fetch origin
git merge origin/main --allow-unrelated-histories
```

Resolve any conflicts, then run:

```powershell
git add .
git commit -m "Merge existing GitHub repository history"
git push -u origin mlops-demo
```

If the repository uses `master` instead of `main`, replace `origin/main` with `origin/master`.

Do not use `git push --force` unless you fully understand the consequences. Force-pushing can overwrite commits on the remote branch.

## Typical future workflow

After making changes to the project:

```powershell
git status
git add .
git commit -m "Describe the change"
git push
```

To create another feature branch from the current branch:

```powershell
git switch -c feature-name
```

To list all local and remote branches:

```powershell
git branch -a
```

To switch back to the main branch:

```powershell
git switch main
```

## Important concepts

- **Working directory:** The files currently on your computer.
- **Staging area:** Files selected by `git add` for the next commit.
- **Commit:** A saved snapshot in the local Git history.
- **Branch:** An independent line of development, such as `mlops-demo`.
- **Remote:** A GitHub repository connected to the local repository.
- **Upstream branch:** The remote branch associated with the local branch.

Creating and pushing `mlops-demo` does not overwrite the existing `main` branch. It creates a separate branch containing your project commit.
