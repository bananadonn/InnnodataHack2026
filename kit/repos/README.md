# Supplied repositories

One real, permissively-licensed open-source repository per language. Your pipeline generates feature tasks on
top of these. Each is a live project with a real test suite and a clean build.

| Language | Repo | Upstream | License | Test runner | Build |
|---|---|---|---|---|---|
| Python | `pallets/click` | https://github.com/pallets/click | BSD-3-Clause | `pytest` | `pip install -e .` |
| JavaScript/TypeScript | `colinhacks/zod` | https://github.com/colinhacks/zod | MIT | `vitest` | `pnpm install && pnpm build` |
| C++ | `open-source-parsers/jsoncpp` | https://github.com/open-source-parsers/jsoncpp | MIT / public-domain | CMake + `ctest` | `cmake -B build && cmake --build build` |

## How to use them

1. **Pin a base commit.** Choose a real, recent, stable commit (a release tag is ideal). Confirm the repo
   builds and its suite is green at that commit *before* generating on top of it. Record the 40-char SHA in
   each package's `task.toml` (`base_commit`).
2. **Build it in `environment/Dockerfile`.** The Dockerfile must be self-contained: start from a public base
   image, clone the upstream repo, `git checkout <base_commit>`, install the toolchain + dependencies, and be
   able to run the test suite. Don't rely on a prebuilt private image (see the interface doc's `docker_image`
   gotcha).
3. **Respect the license** in any redistributed code; keep `license` in `task.toml` accurate.

Finding where a new feature could plausibly live — and standing up the environment — is part of the task.
