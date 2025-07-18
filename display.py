"""Central console utilities for EmailAssistant.

This module provides a single Rich ``Console`` instance and helper
functions for styled output. All user-facing messages should route
through these utilities so appearance can be configured in one place.
"""
from rich.console import Console

console = Console()


def stylize_console(message: str, style: str = "green") -> None:
    """Print ``message`` to the shared console with optional ``style``."""
    console.print(f"[{style}]{message}[/{style}]")
