# Shared Bug Fix

## Request

One screen crashes when a user has no display name.

## TailTrail Direction

Find the shared formatter or data-mapping path before patching the screen:

```js
export function displayName(user) {
  return user.displayName || user.email || "Unknown user";
}
```

If multiple screens use the same formatter, fix it there and keep the UI code unchanged.

## Why This Example Exists

It shows the root-cause preference: one shared guard is easier to review and maintain than scattered caller-specific patches.
