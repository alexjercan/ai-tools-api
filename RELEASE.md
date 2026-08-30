# Release checklist

Use this process for a stable `vX.Y.Z` source release.

1. Start from clean, current `master`. Review completed tasks, public
   documentation, and release scope. Commit all required fixes before release
   preparation.
2. Select the next semantic version. Update `project.version` in
   `pyproject.toml`, then run `uv lock` to update the locked project metadata.
   Move the `CHANGELOG.md` `Unreleased` entries under a `X.Y.Z` heading with the
   release date and update the comparison links. Review the diff and commit the
   release preparation.
3. Run the full repository checks:

   ```bash
   ruff format --check .
   ruff check .
   mypy src
   pytest
   nix flake check -L
   nix build .#ai-tools-api
   git diff --check
   ```

4. Confirm `master` is clean and contains the reviewed version commit. Create
   an annotated tag on that commit:

   ```bash
   git tag -a vX.Y.Z -m "ai-tools-api vX.Y.Z"
   ```

   Release tags are immutable. Never move, replace, or reuse one.
5. Push `master` first. Then push only the new tag:

   ```bash
   git push origin master
   git push origin vX.Y.Z
   ```

   The tag starts `.github/workflows/release.yml`.
6. In GitHub Actions, verify the reusable repository check passed, the package
   build passed, the tag matched `project.version`, and the release job created
   a source-only GitHub Release with generated notes. Do not add build assets;
   Nix consumers use the tagged source flake.
