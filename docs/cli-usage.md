# CLI Usage

## Quickstart
```bash
pip install sgm
sgm start
sgm income cash 100000 "Salary"
sgm expense cash 12000 "Groceries"
sgm pending
sgm render
sgm balances
```

## Core commands
- `sgm start`: first-run setup and preferences.
- `sgm income <account> <amount> "<description>"`: add marked income.
- `sgm expense <account> <amount> "<description>"`: add marked expense.
- `sgm pending`: show marked movements waiting for render.
- `sgm render [snapshot_id]`: render marked movements and clear their mark.
- `sgm balances`: show account balances.

## Advanced command groups
- `sgm account create ...`
- `sgm account list`
- `sgm movement add ...`
- `sgm movement list-marked`
- `sgm transfer move ...`
- `sgm report render-history`
