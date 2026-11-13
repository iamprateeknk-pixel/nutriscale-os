# CI Setup

The CI workflow is already in the repo at `.github/workflows/tests.yml`. On every push to `main` and every pull
request into `main`, GitHub Actions runs all test suites; a green tick means everything passed.

If the file is ever missing: GitHub only lets the repository owner add files under `.github/workflows/`
from the web (apps and tokens without workflow permission cannot). It takes a minute:

1. Open the repo: https://github.com/iamprateeknk-pixel/nutriscale-os
2. **Add file → Create new file** → name it `.github/workflows/tests.yml`
3. Paste the YAML below and **Commit**.

```yaml
name: NutriScale OS Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run all test suites
        run: |
          fail=0
          for t in tests/test_*.py; do
            echo "== $t"
            python3 "$t" || fail=1
          done
          exit $fail
```

Locally the same check is `python3 run_tests.py`.
