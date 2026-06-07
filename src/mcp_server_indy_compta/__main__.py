import argparse
import logging
import os
import sys
import tempfile

from . import __version__
from .mcp_server import mcp

logger = logging.getLogger(__name__)


def cli():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=f"Indy.fr accounting MCP Server (version {__version__})"
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Port to run the MCP server on with HTTP transport (if not specified, stdio transport is implied)",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--silent", action="store_true", help="Show only error messages")
    group.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (can also be set via 'INDY_COMPTA_DEBUG' environment variable)",
    )

    args = parser.parse_args()

    if not args.debug:
        args.debug = os.getenv("INDY_COMPTA_DEBUG", "").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    return args


def configure_logging(args):
    """Configure logging based on command line arguments."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if args.silent:
        log_level = logging.ERROR
    elif args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    if args.port is None:
        # For stdio transport, stdio is reserved for MCP JSON-RPC traffic.
        # Redirect logging to stderr and a log file.
        log_file = os.path.join(tempfile.gettempdir(), f"{__package__}.log")
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stderr),
                logging.FileHandler(log_file, mode="w"),
            ],
        )
        logger.info(f"Logging to stderr and file: {log_file}")
    else:
        logging.basicConfig(level=log_level, format=log_format)
        logger.info("Logging to stdout")


def get_log_level_name(args) -> str:
    if args.silent:
        return logging.getLevelName(logging.ERROR)
    elif args.debug:
        return logging.getLevelName(logging.DEBUG)
    else:
        return logging.getLevelName(logging.INFO)


def main():
    args = cli()
    configure_logging(args)

    try:
        if args.port:
            mcp.run(
                transport="http", port=args.port, log_level=get_log_level_name(args)
            )
        else:
            mcp.run(transport="stdio", log_level=get_log_level_name(args))
    except KeyboardInterrupt:
        pass
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Internal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
