"""Allow ``python -m tailtrail`` to use the stable console entry point."""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
