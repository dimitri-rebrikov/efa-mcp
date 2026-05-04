"""EFA CLI - command-line interface for querying EFA transit APIs.

Usage:
    efa status                          Show current provider URL
    efa set-url <url>                   Set the EFA provider URL
    efa list-providers                  List available EFA providers
    efa find-stop <name>                Find a stop by name
    efa departures <stop-id>            Get departures from a stop
    efa trip <origin-id> <dest-id>      Plan a trip between stops

Options:
    --url <url>     Override the provider URL for this command
    --time <time>   Specify departure/arrival time (ISO 8601 or similar)
    --limit <n>     Maximum number of results (default: 10)
    --arrival       Treat --time as arrival time (for trip command)
"""

import argparse
import asyncio
import sys
from typing import Optional

from efa_lib import EFAClient, get_default_provider


def _create_client(args: argparse.Namespace) -> EFAClient:
    """Create an EFAClient, optionally overriding the provider URL."""
    if args.url:
        return EFAClient(base_url=args.url)
    return EFAClient()


async def cmd_status(client: EFAClient, args: argparse.Namespace) -> None:
    """Show the current provider URL."""
    print(f"Current provider URL: {client.base_url}")


async def cmd_set_url(client: EFAClient, args: argparse.Namespace) -> None:
    """Set the provider URL."""
    client.base_url = args.url
    print(f"Provider URL set to: {client.base_url}")


async def cmd_list_providers(client: EFAClient, args: argparse.Namespace) -> None:
    """List available EFA providers."""
    try:
        providers = await client.list_providers()
        if not providers:
            print("No providers found.")
            return
        print(f"{'Name':<30} {'Country':<15} {'URL'}")
        print("-" * 100)
        for p in providers:
            print(f"{p.name:<30} {p.country:<15} {p.url}")
    except Exception as e:
        print(f"Error fetching providers: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_find_stop(client: EFAClient, args: argparse.Namespace) -> None:
    """Find a stop by name."""
    try:
        stop = await client.find_stop(args.name)
        print(f"Name: {stop.name}")
        print(f"ID:   {stop.id}")
    except Exception as e:
        print(f"Error finding stop: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_departures(client: EFAClient, args: argparse.Namespace) -> None:
    """Get departures from a stop."""
    try:
        departures = await client.departure_monitor(
            args.stop_id, args.time, args.limit
        )
        if not departures:
            print("No departures found.")
            return
        print(
            f"{'Planned':<22} {'Estimated':<22} {'Type':<8} {'Number':<8} {'Direction'}"
        )
        print("-" * 100)
        for d in departures:
            est = d.estimated_time or "-"
            print(
                f"{d.planned_time:<22} {est:<22} {d.type:<8} {d.number:<8} {d.direction}"
            )
    except Exception as e:
        print(f"Error fetching departures: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_trip(client: EFAClient, args: argparse.Namespace) -> None:
    """Plan a trip between stops."""
    try:
        connections = await client.trip_request(
            args.origin_id, args.dest_id, args.time, args.arrival
        )
        if not connections:
            print("No connections found.")
            return
        for i, conn in enumerate(connections, 1):
            print(f"\n=== Connection {i} ===")
            for leg in conn.legs:
                dep_est = (
                    f" (est: {leg.estimated_departure_time})"
                    if leg.estimated_departure_time
                    else ""
                )
                arr_est = (
                    f" (est: {leg.estimated_arrival_time})"
                    if leg.estimated_arrival_time
                    else ""
                )
                print(
                    f"  {leg.departure_station}"
                    f"  {leg.planned_departure_time}{dep_est}"
                )
                print(
                    f"    -> {leg.type} {leg.number} towards {leg.direction}"
                )
                print(
                    f"  {leg.arrival_station}"
                    f"  {leg.planned_arrival_time}{arr_est}"
                )
    except Exception as e:
        print(f"Error planning trip: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Entry point for the EFA CLI."""
    parser = argparse.ArgumentParser(
        description="Query EFA transit APIs from the command line."
    )
    parser.add_argument(
        "--url",
        help="Override the EFA provider URL for this command "
        f"(default: {get_default_provider()})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    subparsers.add_parser("status", help="Show current provider URL")

    # set-url
    set_url_parser = subparsers.add_parser(
        "set-url", help="Set the EFA provider URL"
    )
    set_url_parser.add_argument("url", help="The EFA API provider URL")

    # list-providers
    subparsers.add_parser(
        "list-providers", help="List available EFA API providers"
    )

    # find-stop
    find_stop_parser = subparsers.add_parser(
        "find-stop", help="Find a stop by name"
    )
    find_stop_parser.add_argument("name", help="Name of the stop to search for")

    # departures
    departures_parser = subparsers.add_parser(
        "departures", help="Get departures from a stop"
    )
    departures_parser.add_argument("stop_id", help="Stop identifier")
    departures_parser.add_argument(
        "--time", help="Departure time (ISO 8601 or similar)"
    )
    departures_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of departures"
    )

    # trip
    trip_parser = subparsers.add_parser(
        "trip", help="Plan a trip between stops"
    )
    trip_parser.add_argument("origin_id", help="Origin stop identifier")
    trip_parser.add_argument("dest_id", help="Destination stop identifier")
    trip_parser.add_argument(
        "--time", help="Departure/arrival time (ISO 8601 or similar)"
    )
    trip_parser.add_argument(
        "--arrival",
        action="store_true",
        help="Treat --time as arrival time (default: departure time)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = _create_client(args)

    commands = {
        "status": cmd_status,
        "set-url": cmd_set_url,
        "list-providers": cmd_list_providers,
        "find-stop": cmd_find_stop,
        "departures": cmd_departures,
        "trip": cmd_trip,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        asyncio.run(cmd_func(client, args))


if __name__ == "__main__":
    main()
