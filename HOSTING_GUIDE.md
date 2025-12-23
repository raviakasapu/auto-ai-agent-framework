# Private Distribution: GitHub Pages (Docs) + Git Install (Package)

This guide shows how to host your agent framework for private distribution using a single GitHub repository.

**Repository**: https://github.com/raviakasapu/agent_framework

## Overview

| Component | Method | Access |
|-----------|--------|--------|
| Documentation | GitHub Pages | `https://raviakasapu.github.io/agent_framework/` |
| Package | `pip install git+...` | `pip install git+https://github.com/raviakasapu/agent_framework.git` |

---

## Step 1: Repository Structure

Reorganize the repo to this structure:

```
autoAI-agent-framework/
├── .github/workflows/docs.yml   # Auto-build & deploy docs
├── src/agent_framework/         # Package source
├── docs/                        # Built HTML (GitHub Pages serves this)
├── docs_source/source/          # Sphinx RST/MD source files
├── pyproject.toml
├── README.md
└── LICENSE
```

### Migration Commands

```bash
# From ai_agent_framework_repo directory:

# 1. Move package source to root
cp -r agent-framework-pypi/src .
cp agent-framework-pypi/pyproject.toml .
cp agent-framework-pypi/LICENSE .
cp agent-framework-pypi/README.md .

# 2. Rename sphinx source directory
mv docs/sphinx docs_source

# 3. Build docs to /docs for GitHub Pages
cd docs_source
sphinx-build -b html source ../docs
cd ..

# 4. Commit
git add .
git commit -m "Restructure for GitHub distribution"
```

---

## Step 2: Enable GitHub Pages

1. Go to **Settings → Pages** in your GitHub repo
2. Set **Source**: `Deploy from a branch`
3. Set **Branch**: `main` and folder `/docs`
4. Click **Save**

Your docs will be available at:
```
https://<username>.github.io/<repo-name>/
```

For **private repos**, only authenticated users can access the Pages site.

---

## Step 3: Install Package from Git

### Public Repo

```bash
pip install git+https://github.com/raviakasapu/agent_framework.git
```

### Private Repo (SSH)

```bash
# Requires SSH key configured with GitHub
pip install git+ssh://git@github.com/raviakasapu/agent_framework.git
```

### Private Repo (Token)

```bash
# Using a Personal Access Token (PAT)
pip install git+https://<token>@github.com/raviakasapu/agent_framework.git
```

### Specific Version/Tag

```bash
pip install git+https://github.com/raviakasapu/agent_framework.git@v0.1.0
pip install git+https://github.com/raviakasapu/agent_framework.git@main
pip install git+https://github.com/raviakasapu/agent_framework.git@<commit-sha>
```

### With Optional Dependencies

```bash
pip install "autoAI-agent-framework[all] @ git+https://github.com/raviakasapu/agent_framework.git"
```

---

## Step 4: Use in requirements.txt

```txt
# requirements.txt for dependent projects

# Public repo
autoAI-agent-framework @ git+https://github.com/raviakasapu/agent_framework.git@v0.1.0

# Private repo (SSH) - recommended for CI/CD
autoAI-agent-framework @ git+ssh://git@github.com/raviakasapu/agent_framework.git@main

# With extras
autoAI-agent-framework[observability] @ git+https://github.com/raviakasapu/agent_framework.git
```

---

## Step 5: CI/CD Integration

### GitHub Actions (in consuming project)

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # or a PAT for cross-repo
        run: |
          pip install git+https://${GH_TOKEN}@github.com/raviakasapu/agent_framework.git
          pip install -r requirements.txt
```

### Using Deploy Keys (for CI)

1. Generate SSH key: `ssh-keygen -t ed25519 -C "deploy-key"`
2. Add public key to the **agent_framework** repo as a Deploy Key
3. Add private key to the consuming repo as a secret
4. Configure pip to use SSH:

```yaml
- name: Setup SSH for private deps
  run: |
    mkdir -p ~/.ssh
    echo "${{ secrets.DEPLOY_KEY }}" > ~/.ssh/id_ed25519
    chmod 600 ~/.ssh/id_ed25519
    ssh-keyscan github.com >> ~/.ssh/known_hosts

- name: Install private package
  run: pip install git+ssh://git@github.com/raviakasapu/agent_framework.git
```

---

## pyproject.toml Adjustments

URLs are already configured in `pyproject.toml`:

```toml
[project.urls]
Homepage = "https://github.com/raviakasapu/agent_framework"
Documentation = "https://raviakasapu.github.io/agent_framework/"
Repository = "https://github.com/raviakasapu/agent_framework"
```

---

## Alternative: GitHub Releases with Wheels

For faster installs, publish wheel files as GitHub Release assets:

```bash
# Build wheel
python -m build

# Create a release and upload dist/*.whl
gh release create v0.1.0 dist/*.whl --title "v0.1.0"
```

Install from release:
```bash
pip install https://github.com/raviakasapu/agent_framework/releases/download/v0.1.0/agentic_framework-0.1.0-py3-none-any.whl
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Build docs locally | `cd docs_source && sphinx-build -b html source ../docs` |
| Install from git | `pip install git+https://github.com/<org>/repo.git` |
| Install specific version | `pip install git+...@v0.1.0` |
| Install with extras | `pip install "pkg[extra] @ git+..."` |

---

## Troubleshooting

### "Repository not found" error
- Ensure you have access to the private repo
- For SSH: Check `ssh -T git@github.com` works
- For HTTPS: Verify your token has `repo` scope

### GitHub Pages not updating
- Check Actions tab for workflow errors
- Ensure `docs/` folder is committed
- Wait 2-5 minutes for propagation

### Import errors after install
- Verify `src/` layout in pyproject.toml:
  ```toml
  [tool.setuptools.packages.find]
  where = ["src"]
  ```

