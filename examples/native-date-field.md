# Native Date Field

## Request

Add a date field to a web form.

## TailTrail Direction

Start with the platform control:

```html
<label for="start-date">Start date</label>
<input id="start-date" name="startDate" type="date">
```

Use a custom picker only when the product requires behavior the native input cannot provide, such as a multi-date range UI, custom calendar rules, or a visual design that cannot be met accessibly with the browser control.

## Why This Example Exists

It shows the platform-native preference: avoid owning package upgrades, styling bugs, keyboard behavior, and accessibility fixes when the browser already provides the needed control.
