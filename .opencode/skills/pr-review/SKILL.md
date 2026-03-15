---
name: pr-review
description: Create a pull request for the current branch and trigger an OpenCode review via the /opencode GitHub workflow
---

## What this skill does

Guides you through creating a pull request and requesting an automated code review from OpenCode via the `/opencode` GitHub Actions workflow.

## Steps

### 1. Verify the branch state

- Confirm you are NOT on `main` or `master`.
- Run `git status` to check for uncommitted changes. If there are uncommitted changes, ask the user whether to commit them first.
- Check if the branch has been pushed to the remote. If not, push it with `git push -u origin HEAD`.

### 2. Create the pull request

- Use `gh pr create` to open a PR against the default branch (`main`).
- Write a clear title and body summarizing all commits on the branch (use `git log main..HEAD`).
- Use the standard PR body format:
  ```
  ## Summary
  <bullet points describing the changes>

  ## Changes
  <list of files changed and why>
  ```
- If a PR already exists for the branch, skip creation and use the existing one.

### 3. Write a self-summary of the changes

Before requesting the review, analyze the diff (`git diff main..HEAD`) and compose a concise summary that includes:

- **What was done**: A plain-language explanation of the purpose and nature of the changes (bug fix, new feature, refactor, etc.).
- **Modules affected**: List every top-level module/package directory that was touched (e.g. `backend/application/`, `backend/infrastructure/database/`, `backend/core/`, `docs/`). Group related files under their module.
- **Key decisions**: Briefly note any non-obvious design choices or trade-offs made during implementation.

This summary will be included both in the PR body and in the review request comment so the reviewer has full context.

### 4. Request an OpenCode review

- After the PR is created (or if it already exists), post a comment on the PR to trigger the OpenCode GitHub Actions workflow.
- The comment MUST include the self-summary from step 3 so the reviewer understands what was done and which modules were affected.
- Use the following format:
  ```
  gh pr comment <PR_NUMBER> --body "$(cat <<'EOF'
  /opencode Review this pull request.

  ## Author summary
  <paste the self-summary from step 3 here>

  ## Review instructions
  - Check for code quality issues and potential bugs.
  - Verify adherence to project conventions defined in AGENTS.md (strong typing, no Any, Pydantic models, import root rules, naming conventions, error handling patterns).
  - Check that tests are included for new behavior.
  - Look for missing or outdated documentation in docs/.
  - Suggest improvements where appropriate.
  EOF
  )"
  ```
- This triggers the workflow defined in `.github/workflows/opencode.yml` which responds to `/opencode` commands in comments.

### 5. Report back

- Print the PR URL so the user can navigate to it.
- Let the user know that the OpenCode review has been triggered and will appear as a comment on the PR shortly.

## Important notes

- The repository must have the OpenCode GitHub App installed and the `OPENCODE_API_KEY` secret configured for the workflow to run.
- The workflow is defined in `.github/workflows/opencode.yml` and triggers on `issue_comment` and `pull_request_review_comment` events containing `/opencode` or `/oc`.
- Do NOT force-push or push to `main`/`master` directly.
