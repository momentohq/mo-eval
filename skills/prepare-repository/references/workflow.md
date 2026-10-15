# Prepare a repository for task authoring

Start from an exact repository commit. Record its full 40-character Git ID and inspect the files at
that commit, especially `.mo-eval/config.toml`, before proposing an environment. A working tree or
an image that worked for a different commit is not evidence for this snapshot.

The author supplies a pinned worker image (`name@sha256:<digest>`, `linux/amd64`) when the base has no
committed environment declaration. If the base has one, use its image, platform and setup command
without supplying a second runtime to the helper. Do not choose an image or setup command from a language
label alone. Explain any unsupported or unknown requirement to the author.

For dependencies the tests need offline, use the base's committed `offline_prepare` and
`offline_artifacts`, or supply one explicit preparation command and the artifact roots it leaves.
The lane runs that command once with network access in the pinned image, keeps those roots, and
grades the prepared start tree offline. A command that fails, leaves no declared artifact, overlaps
test files, or conflicts with a committed preparation is refused. The command executes repository
code and fetched dependencies, so inspect it and its sources before approval.

Return an inspectable declaration: base commit, repository identity, pinned image and platform,
setup command if any, preparation command and artifact roots if any, and the evidence used for each
choice. Pass these to the `author-task` workflow. Task build validation is the authoritative check
that the unchanged base fails and the environment supports the verifier. This workflow does not
automatically infer, build or validate a repository runtime.
