import argparse

from .updater import run_update


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["update"])
    parser.add_argument("--config", default="stocks/krx_dashboard/config.json")
    args = parser.parse_args()
    if args.command == "update":
        scores = run_update(args.config)
        print(f"updated {len(scores)} scores")


if __name__ == "__main__":
    main()

