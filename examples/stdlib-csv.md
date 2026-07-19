# Standard Library CSV

## Request

Read a CSV export and sum the `amount` column.

## TailTrail Direction

Use the language tool built for the format before writing a parser:

```python
import csv
from decimal import Decimal

def total_amount(path):
    with open(path, newline="") as file:
        return sum(Decimal(row["amount"]) for row in csv.DictReader(file))
```

Add custom parsing only when the input is not actually CSV or the project already has a shared import utility that should be reused.

## Why This Example Exists

It shows the standard-library preference: less code, fewer parsing bugs, and clearer behavior for common formats.
