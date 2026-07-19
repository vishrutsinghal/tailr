# Compression Policy

TailTrail should reduce tokens without losing exactness where exactness matters.

## Default

Use text slicing, project maps, output summaries, and cache summaries before compression. Compression is optional and off by default.

## Compression Candidates

Compression can be considered for stable, bulky, read-mostly material such as:

- old design background
- old session summaries
- verbose process notes
- large non-normative examples
- historical reports where the gist is enough

## Never Compress

Keep exact text for:

- source code
- diffs and patches
- commands and command output needed for diagnosis
- file paths
- dependency names and versions
- config values
- stack traces
- identifiers, hashes, IDs, and secrets
- authorization, validation, security, privacy, data integrity, and approval rules
- explicit user requirements

## Decision Check

Before compressing, answer:

- Is byte-for-byte text unnecessary for this task?
- Can the source be reopened if exact details are needed?
- Is the material stable enough that a summary will not mislead future work?
- Is the summary marked with its source and refresh condition?

If any answer is no, do not compress.
