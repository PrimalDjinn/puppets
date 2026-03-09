"""Command-line interface for puppets."""

import argparse
import logging
import sys
import json

from puppets import SessionManager
from puppets.exceptions import PuppetsError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="puppets - Automate Chrome through Tor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  puppets run 10                    # Run 10 parallel sessions
  puppets run 100 --workers 20      # Run 100 sessions with 20 workers
  puppets run 50 --headless         # Run in headless mode
  puppets run 5 --output results.json  # Save results to JSON
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run parallel sessions")
    run_parser.add_argument("num_sessions", type=int, help="Number of sessions to run")
    run_parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=10,
        help="Maximum parallel workers (default: 10)",
    )
    run_parser.add_argument(
        "--headless", action="store_true", help="Run browsers in headless mode"
    )
    run_parser.add_argument("-o", "--output", help="Output file for results (JSON)")
    run_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    if args.command == "run":
        try:
            manager = SessionManager(
                max_workers=args.workers,
                headless=args.headless,
            )

            results = manager.run_sessions(num_sessions=args.num_sessions)

            # Print summary
            successful = sum(1 for r in results if r.get("success", False))
            print(f"\n{'='*50}")
            print(f"Results: {successful}/{len(results)} sessions successful")
            print(f"{'='*50}")

            # Show IP addresses
            print("\nSession IPs:")
            for r in results:
                if r.get("success"):
                    print(f"  {r['session_id']}: {r.get('ip', 'N/A')}")

            # Save to file if requested
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"\nResults saved to {args.output}")

            # Exit with error if any failed
            if successful < len(results):
                sys.exit(1)

        except PuppetsError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            sys.exit(130)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
