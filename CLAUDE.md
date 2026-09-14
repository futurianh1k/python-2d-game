# CLAUDE.md
# Claude Code Adapter — Game Development CI/CD · DevOps

@AGENTS.md

## 1. Canonical Policy

Treat `AGENTS.md` as the canonical project-wide engineering policy.

Apply this file as Claude Code-specific execution guidance.

If repository-specific documentation conflicts with generic guidance, inspect the repository and preserve the project-specific rule unless it is unsafe, broken, or the user explicitly requests a change.

---

## 2. Read Before Editing

Before answering repository-specific questions or changing code:

- inspect the relevant files
- inspect existing CI/CD definitions
- inspect build/test/package scripts
- inspect engine/toolchain version files
- inspect `.gitignore` and `.gitattributes` when assets/build outputs are involved
- inspect `git status` before broad edits
- trace the command path from CI entrypoint to the actual build/test/package implementation

Do not speculate about files you have not inspected.

Do not invent scripts, job names, environments, runner labels, engine versions, store channels, or paths.

---

## 3. Default Execution Style

When tools and permissions allow, implement the requested repository change instead of stopping at a hypothetical explanation.

Keep edits:

- minimal
- focused
- reversible
- compatible with current repository conventions

Do not introduce speculative abstractions.

Do not replace the existing CI/CD platform simply because another platform is familiar.

---

## 4. Planning Threshold

Create a short implementation plan before editing when a change affects:

- release pipelines
- production deployment
- store publishing
- signing
- infrastructure
- engine upgrades
- runner images
- Git LFS rules
- artifact versioning
- cache architecture
- build matrix
- database migrations
- multi-platform release flow

The plan should identify:

- affected files
- intended behavior
- validation
- risks
- rollback/recovery

For a trivial syntax fix, work directly and validate proportionally.

---

## 5. Repository-Native Commands

Before inventing commands, check:

- `README*`
- `Makefile`
- task runners
- package scripts
- `scripts/`
- `tools/`
- `Build/`
- engine automation files
- CI workflow files

Prefer repository wrappers over embedding large raw engine command lines directly into CI.

---

## 6. Command Discipline

When executing commands:

- prefer non-interactive modes
- capture the exact failing command
- capture exit codes
- do not repeatedly retry deterministic failures
- do not bypass checks using `--no-verify`
- do not use destructive commands as shortcuts
- do not expose full environment dumps containing secrets

If a command may change production or publish externally, require explicit approval.

---

## 7. Git Safety

Preserve all user work.

Before broad edits:

- inspect `git status`
- identify unrelated uncommitted changes
- do not overwrite unfamiliar modifications

Never run without explicit approval:

- `git reset --hard`
- destructive `git clean`
- branch deletion
- force push
- shared history rewrite
- production tag deletion

Do not commit or push unless explicitly requested or required by the surrounding authorized workflow.

---

## 8. CI/CD Editing Checklist

When changing CI configuration, identify:

1. trigger behavior
2. permissions
3. runner type
4. runner labels/capabilities
5. environment
6. secrets/identity
7. caches
8. artifacts
9. job dependencies
10. concurrency/cancellation
11. deployment side effects
12. release side effects
13. failure artifacts
14. validation method

A valid YAML parser is not sufficient proof that the pipeline works.

Verify referenced paths, scripts, environment variables, files, and commands.

---

## 9. Game Build Validation Levels

Do not imply that every target build can be validated locally.

Separate validation levels:

- configuration validation
- script validation
- compile/build validation
- engine test validation
- cook/package validation
- signing validation
- publishing validation
- production deployment validation

State exactly which level was completed.

---

## 10. Unity Behavior

When Unity is detected:

- read `ProjectSettings/ProjectVersion.txt`
- inspect package lock state
- inspect existing batch-mode wrappers
- preserve existing test conventions
- avoid adding generated directories
- treat licensing material as secret
- inspect cache behavior before modifying it

Do not assume local Unity availability.

---

## 11. Unreal Behavior

When Unreal is detected:

- inspect the `.uproject`
- identify engine version/source-build conventions
- inspect UBT/UAT/BuildGraph usage
- trace compile/cook/package/test wrappers
- preserve DDC behavior unless intentionally changing it
- avoid editing generated project files

Do not assume local Unreal Engine availability.

---

## 12. Failure Diagnosis

When investigating a failure:

- find the first causal error
- identify command and exit code
- quote only the minimal relevant log fragment
- classify the failure as infrastructure, toolchain, source, test, cache, credential, artifact, or deployment related
- inspect recent relevant changes
- determine whether the failure is deterministic or transient
- propose a focused validation step
- prefer the smallest safe correction

Do not hide persistent problems behind retries.

---

## 13. Security

Treat strings that resemble credentials as sensitive.

Never:

- move secrets into tracked files
- echo secret values
- paste private keys into documentation
- add production credentials to local examples
- broaden CI permissions without need

Prefer short-lived identity and least privilege.

---

## 14. Generated Files

Before modifying generated content, identify its source of truth.

Prefer editing:

- source configuration
- templates
- build scripts
- generators

rather than generated output.

If generated files are intentionally versioned, follow the repository's established regeneration process.

---

## 15. Validation Before Completion

Run applicable validation such as:

- YAML/JSON parsing
- CI workflow lint
- shell lint
- PowerShell validation
- unit tests
- engine tests
- build script dry-run
- local build
- container build
- IaC validate/plan
- package validation

If validation cannot run because a required engine, SDK, license, credential, runner, network, or OS is unavailable, state the limitation explicitly.

Do not say `fixed`, `working`, or `passed` without evidence.

---

## 16. Final Response Format

For implementation tasks, report:

### Changed
- files changed
- behavioral change

### Validated
- commands/checks executed
- results

### Not Validated
- external/platform-specific checks that could not be run

### Risks
- remaining assumptions or operational risks

### Next
- the next CI run, build, QA, or release action the user should perform when needed

Keep the response operational and evidence-based.
