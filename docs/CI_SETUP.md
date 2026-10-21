# CI Setup — ek chhota manual kadam (sirf ek baar)

GitHub ki suraksha ke kaaran koi bhi app/API `.github/workflows/` folder me file **nahi** daal sakta —
ye file sirf repo ke malik (tum) web se add kar sakte ho. 1 minute lagega:

1. Repo kholo: https://github.com/iamprateeknk-pixel/nutriscale-os
2. **Add file → Create new file** → naam likho: `.github/workflows/tests.yml`
3. Neeche wala pura code paste karke **Commit** kar do.

Uske baad har push par saare tests apne aap GitHub par chala karenge (hari tick = sab pass).

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
      - name: Saare test suites chalao
        run: |
          fail=0
          for t in tests/test_*.py; do
            echo "== $t"
            python3 "$t" || fail=1
          done
          exit $fail
```

_Note: Yahi file local project me `.github/workflows/tests.yml` par bhi rakhi hai._
