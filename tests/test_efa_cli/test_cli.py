"""Tests for the EFA CLI.

These tests verify CLI argument parsing and output formatting.
They mock the EFAClient to avoid real API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from efa_lib import Stop, Departure, TripConnection, TripLeg


class TestCLIArgumentParsing:
    """Test that CLI arguments are parsed correctly."""

    def test_status_command(self):
        """Test 'status' command parsing."""
        from efa_cli.cli import main as cli_main

        with patch("sys.argv", ["efa", "status"]):
            with patch("efa_cli.cli.cmd_status") as mock_cmd:
                try:
                    cli_main()
                except SystemExit:
                    pass
                mock_cmd.assert_called_once()

    def test_set_url_command(self):
        """Test 'set-url' command parsing."""
        from efa_cli.cli import main as cli_main

        with patch("sys.argv", ["efa", "set-url", "https://example.com/"]):
            with patch("efa_cli.cli.cmd_set_url") as mock_cmd:
                try:
                    cli_main()
                except SystemExit:
                    pass
                mock_cmd.assert_called_once()

    def test_find_stop_command(self):
        """Test 'find-stop' command parsing."""
        from efa_cli.cli import main as cli_main

        with patch("sys.argv", ["efa", "find-stop", "Stuttgart Hbf"]):
            with patch("efa_cli.cli.cmd_find_stop") as mock_cmd:
                try:
                    cli_main()
                except SystemExit:
                    pass
                mock_cmd.assert_called_once()

    def test_departures_command(self):
        """Test 'departures' command parsing."""
        from efa_cli.cli import main as cli_main

        with patch("sys.argv", ["efa", "departures", "de:08111:1"]):
            with patch("efa_cli.cli.cmd_departures") as mock_cmd:
                try:
                    cli_main()
                except SystemExit:
                    pass
                mock_cmd.assert_called_once()

    def test_departures_with_options(self):
        """Test 'departures' with --time and --limit."""
        from efa_cli.cli import main as cli_main

        with patch(
            "sys.argv",
            ["efa", "departures", "de:08111:1", "--time", "2026-05-01T10:00:00", "--limit", "5"],
        ):
            with patch("efa_cli.cli.cmd_departures") as mock_cmd:
                try:
                    cli_main()
                except SystemExit:
                    pass
                mock_cmd.assert_called_once()

    def test_trip_command(self):
        """Test 'trip' command parsing."""
        from efa_cli.cli import main as cli_main

        with patch("sys.argv", ["efa", "trip", "de:08111:1", "de:08111:2"]):
            with patch("efa_cli.cli.cmd_trip") as mock_cmd:
                try:
                    cli_main()
                except SystemExit:
                    pass
                mock_cmd.assert_called_once()

    def test_trip_with_options(self):
        """Test 'trip' with --time and --arrival."""
        from efa_cli.cli import main as cli_main

        with patch(
            "sys.argv",
            ["efa", "trip", "de:08111:1", "de:08111:2", "--time", "2026-05-01T10:00:00", "--arrival"],
        ):
            with patch("efa_cli.cli.cmd_trip") as mock_cmd:
                try:
                    cli_main()
                except SystemExit:
                    pass
                mock_cmd.assert_called_once()

    def test_list_providers_command(self):
        """Test 'list-providers' command parsing."""
        from efa_cli.cli import main as cli_main

        with patch("sys.argv", ["efa", "list-providers"]):
            with patch("efa_cli.cli.cmd_list_providers") as mock_cmd:
                try:
                    cli_main()
                except SystemExit:
                    pass
                mock_cmd.assert_called_once()

    def test_no_command_shows_help(self):
        """Test that no command shows help and exits."""
        from efa_cli.cli import main as cli_main

        with patch("sys.argv", ["efa"]):
            with pytest.raises(SystemExit):
                cli_main()

    def test_unknown_command_shows_error(self):
        """Test that unknown command shows error."""
        from efa_cli.cli import main as cli_main

        with patch("sys.argv", ["efa", "unknown-command"]):
            with pytest.raises(SystemExit):
                cli_main()


class TestCLIOutput:
    """Test CLI output formatting with mocked client."""

    @pytest.mark.asyncio
    async def test_status_output(self, capsys):
        """Test status command output."""
        from efa_cli.cli import cmd_status
        from efa_lib import EFAClient

        client = EFAClient(base_url="https://www.efa.de/efa/")
        args = type("Args", (), {"url": None})()

        await cmd_status(client, args)
        captured = capsys.readouterr()
        assert "https://www.efa.de/efa/" in captured.out

    @pytest.mark.asyncio
    async def test_find_stop_output(self, capsys):
        """Test find-stop command output."""
        from efa_cli.cli import cmd_find_stop
        from efa_lib import EFAClient

        client = EFAClient(base_url="https://www.efa.de/efa/")
        args = type("Args", (), {"name": "Stuttgart Hbf", "url": None})()

        # Mock the client's find_stop method
        with patch.object(client, "find_stop", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = Stop(name="Stuttgart Hauptbahnhof", id="de:08111:1")
            await cmd_find_stop(client, args)

        captured = capsys.readouterr()
        assert "Stuttgart Hauptbahnhof" in captured.out
        assert "de:08111:1" in captured.out

    @pytest.mark.asyncio
    async def test_departures_output(self, capsys):
        """Test departures command output."""
        from efa_cli.cli import cmd_departures
        from efa_lib import EFAClient

        client = EFAClient(base_url="https://www.efa.de/efa/")
        args = type("Args", (), {"stop_id": "de:08111:1", "time": None, "limit": 10, "url": None})()

        mock_departures = [
            Departure(
                planned_time="2026-05-01T19:43:00Z",
                estimated_time="2026-05-01T19:45:00Z",
                type="0",
                number="S1",
                direction="Stuttgart",
            ),
            Departure(
                planned_time="2026-05-01T19:50:00Z",
                type="0",
                number="S2",
                direction="Flughafen",
            ),
        ]

        with patch.object(client, "departure_monitor", new_callable=AsyncMock) as mock_dm:
            mock_dm.return_value = mock_departures
            await cmd_departures(client, args)

        captured = capsys.readouterr()
        assert "S1" in captured.out
        assert "S2" in captured.out
        assert "Stuttgart" in captured.out
        assert "Flughafen" in captured.out

    @pytest.mark.asyncio
    async def test_trip_output(self, capsys):
        """Test trip command output."""
        from efa_cli.cli import cmd_trip
        from efa_lib import EFAClient

        client = EFAClient(base_url="https://www.efa.de/efa/")
        args = type("Args", (), {
            "origin_id": "de:08111:1",
            "dest_id": "de:08111:2",
            "time": None,
            "arrival": False,
            "url": None,
        })()

        mock_connections = [
            TripConnection(legs=[
                TripLeg(
                    type="0",
                    number="S1",
                    direction="Flughafen",
                    departure_station="Stuttgart Hbf",
                    planned_departure_time="2026-05-01T19:43:00Z",
                    arrival_station="Stuttgart Flughafen",
                    planned_arrival_time="2026-05-01T19:55:00Z",
                )
            ])
        ]

        with patch.object(client, "trip_request", new_callable=AsyncMock) as mock_trip:
            mock_trip.return_value = mock_connections
            await cmd_trip(client, args)

        captured = capsys.readouterr()
        assert "Connection 1" in captured.out
        assert "Stuttgart Hbf" in captured.out
        assert "Stuttgart Flughafen" in captured.out
        assert "S1" in captured.out
