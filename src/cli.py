#!/usr/bin/env python3
"""
Workshop Translator CLI
Command-line interface for running the workshop translator locally
"""

import sys
import argparse

# Local execution
from main import run_cli


def main():
    """CLI main entry point"""
    parser = argparse.ArgumentParser(
        description="Workshop Translator - AI-powered workshop document translation agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  wstranslator
  
  # Single query
  wstranslator "analyze workshop"

Notes:
  - Requires Amazon Bedrock model access permissions
  - Configure AWS credentials: aws configure (or isengardcli)
  - See cli_remote_backup.py for remote mode
        """
    )
    
    parser.add_argument(
        'prompt',
        type=str,
        nargs='?',
        help='Single query prompt (interactive mode if omitted)'
    )
    
    args = parser.parse_args()
    
    # Single query mode
    if args.prompt:
        print(f"\n⚠️  Single query mode is not yet implemented.")
        print(f"Please use interactive mode: wstranslator\n")
        sys.exit(1)
    
    # Run interactive mode
    run_cli()


if __name__ == "__main__":
    main()
