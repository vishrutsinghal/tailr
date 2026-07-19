# Preserve The Guard

## Request

Simplify a file download helper.

## TailTrail Direction

Keep the safety check even if it makes the function longer:

```js
import path from "node:path";

export function safeReportPath(baseDir, filename) {
  const resolved = path.resolve(baseDir, filename);
  if (!resolved.startsWith(path.resolve(baseDir) + path.sep)) {
    throw new Error("Invalid report path");
  }
  return resolved;
}
```

Shorter code is not better if it allows path traversal, data loss, authorization bypass, or invalid input to cross a trust boundary.

## Why This Example Exists

It shows the safeguard rule: TailTrail reduces unnecessary code, not necessary protection.
