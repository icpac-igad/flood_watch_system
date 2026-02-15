# Geomanager Releases

Geomanager is released as a Python package via GitHub Releases.

## Current Version

**v0.7.2** (Beta)

## Installing a Specific Version

```bash
# Latest release
pip install geomanager

# Specific version from GitHub
pip install git+https://github.com/icpac-igad/flood_watch_system.git@geomanager-v0.7.2#subdirectory=eafw_cms/geomanager
```

## Release Process

Releases are automated via GitHub Actions. To create a new release:

1. Update the version in `eafw_cms/geomanager/pyproject.toml`
2. Commit and push to `main`
3. Create a git tag: `git tag geomanager-v0.X.Y && git push origin geomanager-v0.X.Y`
4. GitHub Actions will automatically build and publish the package

## Changelog

See [GitHub Releases](https://github.com/icpac-igad/flood_watch_system/releases) for the full changelog.
