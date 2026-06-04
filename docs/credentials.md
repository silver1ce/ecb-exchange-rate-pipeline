# Credentials (no secrets in this repo)

This project never stores GitHub tokens, passwords, or API keys in git.

## Where your GitHub access is stored

On this Mac, HTTPS Git access to GitHub is handled by **macOS Keychain** via Git’s credential helper:

```bash
# See which helper Git uses
git config --global credential.helper

# Typical on macOS
git credential-osxkeychain
```

When you push or pull, Git reads the token from Keychain. You do not need a token file in the project.

## Application secrets (pipeline)

Copy `.env.example` to `.env` locally (already in `.gitignore`):

```bash
cp .env.example .env
```

Set `DATABASE_URL` and other values only in `.env` — never commit `.env`.

## If you need a new GitHub token

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens**
2. Create a token with `repo` scope (for private repos).
3. Store it once when Git prompts on push:

   ```bash
   git push origin main
   ```

   macOS will offer to save it in Keychain.

4. Revoke old tokens you no longer use.

## Do not save tokens here

| Bad | Good |
|-----|------|
| `token.txt` in the repo | Keychain / `gh auth login` |
| Token in `README.md` | `.env` (gitignored) |
| Token in Cursor rules or chat | GitHub Secrets (for CI only) |

For CI, use **GitHub Actions secrets** in the repository settings, not files in the codebase.
