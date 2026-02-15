# Geomanager Releases

Geomanager is released as a Python package via GitHub Releases.

## Current Version

**v0.7.2** (Beta)

## Installing Geomanager

### From GitHub Release

```bash
pip install git+https://github.com/icpac-igad/flood_watch_system.git#subdirectory=eafw_cms/geomanager
```

### Specific Version

```bash
pip install git+https://github.com/icpac-igad/flood_watch_system.git@geomanager-v0.7.2#subdirectory=eafw_cms/geomanager
```

### From Downloaded Wheel

Download the `.whl` file from [GitHub Releases](https://github.com/icpac-igad/flood_watch_system/releases), then:

```bash
pip install geomanager-0.7.2-py3-none-any.whl
```

## Release Process

Geomanager releases are automated via GitHub Actions. Follow these steps to publish a new version:

### Step 1: Update the Version

Edit `eafw_cms/geomanager/pyproject.toml` and bump the version number:

```toml
[project]
name = "geomanager"
version = "0.8.0"  # <-- update this
```

### Step 2: Commit and Push

```bash
git add eafw_cms/geomanager/pyproject.toml
git commit -m "Bump geomanager to v0.8.0"
git push origin eafw
```

Merge to main:

```bash
git checkout main
git merge eafw
git push origin main
git checkout eafw
```

### Step 3: Create and Push a Tag

The tag **must** follow the format `geomanager-vX.Y.Z`:

```bash
git tag geomanager-v0.8.0
git push origin geomanager-v0.8.0
```

!!! warning "Important"
    Make sure the commit message does **not** contain `[skip ci]`, otherwise the release workflow will not trigger.

### Step 4: Verify the Release

The GitHub Actions workflow will automatically:

1. Build the Python package (`.whl` and `.tar.gz`)
2. Create a GitHub Release with auto-generated release notes
3. Attach the built packages as downloadable assets

Check the release at: [github.com/icpac-igad/flood_watch_system/releases](https://github.com/icpac-igad/flood_watch_system/releases)

### Manual Trigger

You can also trigger the release workflow manually from the Actions tab:

1. Go to **Actions** > **Release Geomanager Package**
2. Click **Run workflow**
3. Select the branch/tag

## Versioning

Geomanager follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes to models, APIs, or database schema
- **MINOR** (0.X.0): New features, new layer types, new management commands
- **PATCH** (0.0.X): Bug fixes, dependency updates, minor improvements

## Changelog

See [GitHub Releases](https://github.com/icpac-igad/flood_watch_system/releases) for the full changelog with auto-generated notes.
