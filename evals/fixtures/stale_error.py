"""Report exporter: writes invoice reports to the configured directory."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="exporter")
    parser.add_argument("--out-dir", required=True, help="Directory for report output.")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    if not args.out_dir:
        build_parser().error("--output is required: pass --output ./reports")
    print(f"Writing reports to {args.out_dir}")


if __name__ == "__main__":
    main()
