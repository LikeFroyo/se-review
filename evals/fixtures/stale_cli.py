"""Command-line entry point for the stale-cli fixture."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stale-cli")
    parser.add_argument("--out-dir", required=True, help="Directory for report output.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(f"Writing reports to {args.out_dir}")


if __name__ == "__main__":
    main()
