# Prompt History

This document tracks the prompts used during development to demonstrate working methodology and AI-assisted workflow.

---

## Prompt 1: Initial Planning

> I am working on a technical test at `/home/james/Code/Zego_Test`
>
> Read `/home/james/Code/Zego_Test/python/README.md`
>
> We need to come up with a comprehensive plan considering options and possible problems we might encounter.
>
> Please maintain a record of all prompts throughout this session to demonstrate my working process during the interview.

**Result:** Created initial [PLAN.md](PLAN.md) with architecture options, component breakdown, and risk mitigations.

---

## Prompt 2: Document the Plan

> We need to write this plan down to a markdown file.

**Result:** Saved comprehensive plan to `PLAN.md`.

---

## Prompt 3: Deep Dive on Search Strategy

> Let's first interrogate the plan and consider speed - for example, depth-first vs breadth-first search.
>
> To show progression, we should write a `PLAN_v2.md` to demonstrate development of the design.

**Result:** Created [PLAN_v2.md](PLAN_v2.md) with detailed BFS vs DFS analysis, concurrency architecture, and speed optimizations.

---

## Prompt 4: Create Prompts Log

> *(This prompt - creating PROMPTS.md to track all prompts for interview demonstration)*

**Result:** Created this file.

---

## Prompt 5: Begin Implementation

> I have reviewed the plan documents. Let's begin the implementation. At each stage we should stop, review the code and tests before moving on.

**Result:** Started incremental implementation with review checkpoints. Implemented `url_utils.py` with 32 tests.

---

## Prompt 6: Continue After Review

> Output this review to a file, then continue as all looks good.

**Result:** Created `REVIEWS.md` to track code reviews. Continued implementing `parser.py`, `crawler.py`, and `__main__.py` with tests at each stage.

---

## Summary of Implementation

The complete implementation was built iteratively:

1. **url_utils.py** - URL normalization, domain checking, filtering (33 tests)
2. **parser.py** - HTML link extraction with BeautifulSoup/lxml (27 tests)
3. **crawler.py** - Async BFS crawler with aiohttp (16 tests)
4. **__main__.py** - CLI with streaming output, error handling

**Total:** 76 tests, all passing. Code passes mypy and ruff checks.

---

## Prompt 7: Restructure Documentation

> We need to split the README out so the new stuff we have should be in the README but the original stuff should be moved to a file named TASK. Then I want to move all the docs we have created to a docs directory.

**Result:**
- Created `docs/` directory
- Moved original test requirements to `docs/TASK.md`
- Updated `README.md` with only implementation content
- Moved `PLAN.md`, `PLAN_v2.md`, `PROMPTS.md`, `REVIEWS.md` to `docs/`

---

*Development complete.*
