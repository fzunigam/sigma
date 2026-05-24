# Auto-Compile Frontend Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure the web frontend dashboard works out-of-the-box when running `sgm web` on a fresh package installation, by detecting the `web` source directory dynamically, building assets, copying them to the running package's `static` directory, and building assets in the PyPI release workflow.

**Architecture:** 
1. Dynamically locate the `web` directory relative to the running CLI file or the current working directory.
2. Build the Next.js assets to static output files and copy them to the running Python package's `static` directory if different from the build directory.
3. Integrate web dashboard compilation into the PyPI GitHub Actions workflow and the developer `Makefile` installation step.

**Tech Stack:** Python 3.12, Setuptools, Node.js, Next.js, GitHub Actions, Makefile

---

## Task 1: Refactor `find_web_src_dir` & Auto-Compile in `cli.py`

**Files:**
- Modify: `src/sgm/cli.py`

**Step 1: Write implementation**
- Extract a helper `find_web_src_dir()` that looks:
  1. At `../../web` relative to `__file__`.
  2. Traverses upwards from `os.getcwd()` checking for `web/package.json`.
- In `web_cmd`:
  - If `index_file` does not exist:
    - Invoke `find_web_src_dir()`.
    - If found:
      - Compile using `npm install` and `npm run build`.
      - Check if the build output directory `os.path.abspath(os.path.join(web_src_dir, "..", "src", "sgm", "interface", "web", "static"))` is different from the running `static_dir`.
      - If different, copy the built assets using `shutil.copytree` (overwriting the destination if it exists).

---

## Task 2: Update Github Actions Release Workflow

**Files:**
- Modify: `.github/workflows/release-pypi.yml`

**Step 1: Write implementation**
- Add `setup-node` step.
- Cache npm dependencies.
- Build the web frontend: run `npm ci` and `npm run build` inside the `web/` directory before building the wheel with `python -m build`.

---

## Task 3: Update Makefile Installation Target

**Files:**
- Modify: `Makefile`

**Step 1: Write implementation**
- Check if `npm` is available.
- If it is, run `npm install` and `npm run build` in the `web` directory.
- Then run `pip install -e`.

---

## Task 4: Write Unit Tests

**Files:**
- Modify: `tests/smoke/test_web_integration.py`

**Step 1: Write tests**
- Verify `find_web_src_dir()` locates `web` dynamically in CWD parents.
- Verify the copy logic runs when build output and running static folders differ.
- Verify no-op when they are the same.
