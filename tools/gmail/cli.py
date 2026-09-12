#!/usr/bin/env python3
"""Command-line interface for Master Agent Gmail integration."""

import argparse
import sys
from pathlib import Path

# Ensure package directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
import client


def cmd_status(args):
    """Display account profile and message statistics."""
    profile = client.get_profile()
    print("=" * 50)
    print(" GMAIL ACCOUNT STATUS")
    print("=" * 50)
    print(f"Email Address : {profile.get('emailAddress')}")
    print(f"Total Messages: {profile.get('messagesTotal')}")
    print(f"Total Threads : {profile.get('threadsTotal')}")
    print(f"History ID    : {profile.get('historyId')}")


def cmd_list(args):
    """List recent messages matching search query."""
    messages = client.list_messages(query=args.query, max_results=args.max)
    if not messages:
        print("No messages found matching query.")
        return

    print(f"Found {len(messages)} message(s):\n")
    for i, m in enumerate(messages, 1):
        print(f"[{i}] ID: {m['id']}")
        print(f"    Date   : {m['date']}")
        print(f"    From   : {m['from']}")
        print(f"    Subject: {m['subject']}")
        print(f"    Snippet: {m['snippet'][:80]}...")
        print("-" * 50)


def cmd_read(args):
    """Read the full content of a specific message ID."""
    msg = client.get_message(args.id)
    print("=" * 60)
    print(f"Subject: {msg['subject']}")
    print(f"From   : {msg['from']}")
    print(f"To     : {msg['to']}")
    print(f"Date   : {msg['date']}")
    print(f"ID     : {msg['id']}")
    print("=" * 60)
    print(msg['body'])
    print("=" * 60)


def cmd_send(args):
    """Send an email."""
    result = client.send_message(
        to=args.to,
        subject=args.subject,
        body=args.body,
        cc=args.cc
    )
    print(f"Message sent successfully! ID: {result.get('id')}")


def main():
    parser = argparse.ArgumentParser(description="Master Agent Gmail CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Check Gmail account status")
    p_status.set_defaults(func=cmd_status)

    # list
    p_list = subparsers.add_parser("list", help="List/search messages")
    p_list.add_argument("-q", "--query", default="", help="Gmail search query")
    p_list.add_argument("-m", "--max", type=int, default=5, help="Max results (default: 5)")
    p_list.set_defaults(func=cmd_list)

    # read
    p_read = subparsers.add_parser("read", help="Read a message by ID")
    p_read.add_argument("id", help="Message ID")
    p_read.set_defaults(func=cmd_read)

    # send
    p_send = subparsers.add_parser("send", help="Send an email")
    p_send.add_argument("--to", required=True, help="Recipient email")
    p_send.add_argument("--subject", required=True, help="Subject line")
    p_send.add_argument("--body", required=True, help="Body text")
    p_send.add_argument("--cc", default=None, help="CC recipient")
    p_send.set_defaults(func=cmd_send)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
