"""YouTube Shorts Generation Pipeline — CLI entry point.

Usage:
    # Interactive mode (prompts you for keywords & description):
    python -m src.main

    # Quick mode with inline args:
    python -m src.main --keywords "python,coding,tricks" --description "Show 3 mind-blowing Python one-liners with energetic pacing"

    # Skip upload:
    python -m src.main --no-upload
"""

import argparse
from .pipeline import Pipeline


def _prompt_input(label: str, hint: str = "") -> str:
    """Prompt the user for input with an optional hint."""
    if hint:
        print(f"\n  {hint}")
    value = input(f"  {label}: ").strip()
    return value


def _interactive_brief() -> dict:
    """Walk the user through an interactive brief for the Short."""
    print("\n" + "=" * 60)
    print("  YouTube Shorts Generator — New Video Brief")
    print("=" * 60)

    keywords = _prompt_input(
        "Keywords (comma-separated)",
        "What is the video about? Enter a few keywords.\n"
        "  Example: python, coding tips, one-liners",
    )

    description = _prompt_input(
        "Description",
        "Describe in a few sentences what the Short should look like and contain.\n"
        "  Example: Fast-paced, show 3 Python tricks with code on screen,\n"
        "  casual tone, ends with a follow CTA.",
    )

    return {
        "keywords": [k.strip() for k in keywords.split(",") if k.strip()],
        "description": description,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate and upload a YouTube Short from a creative brief"
    )
    parser.add_argument(
        "-k", "--keywords",
        help='Comma-separated keywords (e.g. "python,AI,tips")',
    )
    parser.add_argument(
        "-d", "--description",
        help="A few sentences describing what the Short should contain and look like",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip YouTube upload (just generate the video)",
    )
    args = parser.parse_args()

    # If keywords or description missing, go interactive
    if args.keywords and args.description:
        brief = {
            "keywords": [k.strip() for k in args.keywords.split(",") if k.strip()],
            "description": args.description,
        }
    else:
        brief = _interactive_brief()

    if not brief["keywords"]:
        print("Error: At least one keyword is required.")
        return

    print(f"\n  Keywords:    {', '.join(brief['keywords'])}")
    print(f"  Description: {brief['description']}\n")

    pipeline = Pipeline()
    pipeline.run(brief, upload=not args.no_upload)


if __name__ == "__main__":
    main()
