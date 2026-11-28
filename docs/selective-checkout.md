# Obtain the tools without materializing the full archive

Some historical root filenames exceed common filesystem component limits or contain characters unsupported on some platforms. A full checkout may fail even when Git has successfully obtained the repository. The archive names are intentional historical records; this procedure does not rename or remove them.

For a **new working directory**, use a selective checkout with a recent Git:

```sh
git clone --no-checkout --branch main https://github.com/levelinglucy/Emergence-resources.git
cd Emergence-resources
git sparse-checkout set --no-cone "/README.md" "/LICENSE" "/The sandpile" "/Word ants" "/the fairy ring cipher" "/mayas mirrored sentences" "/docs/" "/tests/" "/sols-ember/"
git checkout main
git status --short
```

Check each command succeeds before continuing. A clean checkout prints no changes in the final command. The quoted, root-anchored patterns are intentional: cone mode would also include root-level archival files. The directory patterns include their descendants. If a later revision adds incompatible names inside a selected directory, revisit the patterns rather than rename historical material.

This obtains the selected scripts, documentation, tests, Sol's Ember package and root terms/license; it does not install dependencies or run any of the programs. Refer to the individual developer notes in this directory and the Sol's Ember README for project-specific instructions.

The complete tracked tree remains inspectable with `git ls-tree -r HEAD`. This is a reduced working view, not a complete filesystem export or independent backup. Do not disable sparse checkout merely to inspect omitted archival paths on an incompatible filesystem. Avoid broadening the patterns without checking the names first.

Validation scope: the selected paths were inspected at main revision `a0e3e0fc9f6c9ce6e2a638895c72512fbf4b2b19`. The command sequence was exercised on Linux, Git 2.47.3, using a disposable synthetic repository containing the selected directory layout and deliberately incompatible root names. All 27 selected fixture files materialized, nine excluded files remained absent from the working tree, all 36 remained tracked, HEAD and tree identifiers were unchanged, and the working tree was clean. The actual remote clone, Windows, iOS, other Git versions and program execution were not tested.

Reference: [Git sparse-checkout manual](https://git-scm.com/docs/git-sparse-checkout.html). Non-cone mode has performance and compatibility trade-offs; it is chosen here for the precise file patterns rather than as general Git advice.
