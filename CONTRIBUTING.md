# Contributing

## 1. Use an explicit branch name (instead of main/dev)

Branch name should be small but clearly related to the suggested changes:

```bash
# Create your feature branch 
git checkout -b my-new-feature
```

## 2. Use Conventional Commits

```bash
<type>([optional scope]): <description>

[optional body]

[optional footer(s)]
```

- `fix`: a commit that fixes a bug.
- `feat`: a commit that adds new functionality.
- `refactor`: a commit that only has semantic changes, no functional effect.
- `build`: a commit that includes changes that affect the build system or external *dependencies*
- `deploy`: a commit that either includes a deployment , or triggers one on a hosted envireonment like AWS.
- `docs`: a commit that adds or improves documentation.
- `test`: a commit that adds unit tests.
- `revert`: a commit that reverts a previous change.
- `chore`: a catch-all type for any other commits. For instance, if you're implementing a single feature and it makes sense to divide the work into multiple commits, you should mark one commit as feat and the rest as chore.

## 2. Check linter and formatter errors

Run this before pushing your changes:

```bash
black --check src >formatter.txt
find src -type f -name "*.py" | xargs pylint >linter.txt
```

This will create 2 files for black and pylint errors, then you can evaluate the outputs.
