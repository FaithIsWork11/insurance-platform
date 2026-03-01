# Git Commands Cheat Sheet (Enterprise Workflow)

This guide covers the Git commands you’ll use most while building and maintaining this project.

---

## 1) Check Where You Are + Repo Status

### `pwd`
Shows your current folder path (helps ensure you’re in the right directory).
```bash
pwd


# Lists files and folders in the current directory.

tree -L 3 -I "venv|.venv|__pycache__|.git"




ls

Lists files and folders in the current directory.

ls

git status

Shows:
Modified files
Staged files (ready to commit)
Untracked files (new files not added yet)
git status

2) Inspect Changes Before Committing
git diff
Shows changes that are NOT staged yet.
git diff
git diff <file>
Shows changes in a specific file.
git diff app/routers/auth.py
git diff --staged
Shows changes that ARE staged and ready to commit.
git diff --staged
3) Stage Files (Prepare for Commit)
git add <file>
Stage one file.
git add app/routers/auth.py
git add .
Stage all modified and new files in the current directory.
git add .
git restore --staged <file>
Unstage a file (removes it from next commit but keeps your edits).
git restore --staged pyproject.toml
4) Commit Changes
git commit -m "message"
Creates a commit snapshot with a message.
git commit -m "Wire rate limiting into auth login endpoint"
Enterprise Tip:
Keep commit messages clear and outcome-focused.
Example: Add audit logging to login endpoint
Avoid vague messages like: fix stuff
5) Sync With GitHub
git pull origin main
Download latest changes from GitHub.
git pull origin main
git push origin main
Upload your commits to GitHub.
git push origin main
6) Branching (Safe Development)
git branch
List branches.
git branch
git checkout -b feature/name
Create and switch to a new branch.
git checkout -b feature/rate-limit
git checkout main
Switch back to main branch.
git checkout main
git merge feature/name
Merge a branch into your current branch.
git merge feature/rate-limit
Recommended Workflow:
Create feature branch
Commit work
Push branch
Open Pull Request
Merge into main
7) Undo / Fix Mistakes

git restore <file>

Discard local changes to a file (danger: deletes edits).

git restore app/routers/auth.py
git reset --soft HEAD~1
Undo last commit but keep changes staged.
git reset --soft HEAD~1
git reset --hard HEAD~1
Undo last commit and delete changes (danger).
git reset --hard HEAD~1
8) View History
git log --oneline
Compact commit history.
git log --oneline
git show <commit>
See details of a commit.
git show 2501ea7
git blame <file>
See who changed each line and when.
git blame app/routers/auth.py
9) Remote Information
git remote -v
Shows the GitHub repository URL connected to this project.
git remote -v
10) Daily Enterprise Workflow
Start work:
git pull origin main
git status
After making changes:
git diff
Stage + Commit + Push:
git add .
git commit -m "Clear description of change"
git push origin main
Enterprise Commit Message Examples
Add audit log helper and wire login events
Implement auth rate limiting
Fix UUID handling in register flow
Refactor response envelope into core module
Add RBAC enforcement tests

