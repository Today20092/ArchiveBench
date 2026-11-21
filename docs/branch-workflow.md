# Git workflow

`main` is the only long-lived branch. Each task gets its own branch and pull request into `main`; there is no integration branch and no stacked PRs.

## Work on a task

1. Work in a worktree the host manages, based on current `origin/main`. A T3 Code thread on the main checkout moves itself with `t3_worktree_handoff` before editing; the project's worktree script runs `uv sync` and `pnpm install --frozen-lockfile`. Without host worktree tools, use `git worktree add` and run both.
2. Commit work in progress instead of using `git stash`: stashes are shared by every worktree.
3. Make the change and run the checks in [development](development.md) and complete the [documentation review](development.md#pull-request-documentation-review).
4. End every code task with a commit and a pull request to `main`, without being asked. Opening a PR is safe; only a merge changes `main`; nothing deploys.
5. The `source` checks run on the PR. Watch them and fix failures until they pass. To merge without waiting, queue it with `gh pr merge --auto --merge`; GitHub merges once the required checks pass.
6. Merge only when the user asks, with a merge commit.

Fetch before choosing a base. Use `git pull --ff-only` to advance a local `main`; inspect divergent histories and merge deliberately. Never force-push `main`.

## What runs where

| Event | Effect |
| --- | --- |
| Pull request, any push | [Check](../.github/workflows/check.yml) runs formatting, lint, types, tests, report build and package build |
| Monthly | [Dependabot](../.github/dependabot.yml) opens one grouped minor-and-patch PR per ecosystem; majors one PR each. [Auto-merge](../.github/workflows/dependabot-auto-merge.yml) queues minor and patch PRs; majors wait for a person |

Releases are separate; see [release notes](release-notes.md).

## Repository controls

`main` requires a pull request, the `source` check and resolved conversations; rules apply to administrators, and force pushes and deletion are blocked. It does not require branches to be up to date, since nothing deploys from `main`. Auto-merge is allowed and merged branches are deleted automatically.

## Cleanup

GitHub deletes a merged PR's branch. Remove the task's worktree through the host (or `git worktree remove`) once it has no uncommitted or unmerged work.
