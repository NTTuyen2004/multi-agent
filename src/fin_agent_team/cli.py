"""Simple CLI to run the Supervisor and print a report."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from pathlib import Path

from .supervisor import Supervisor
from .conversation_memory import ConversationMemory


def _pretty(state: Any) -> str:
    # Safe serializer that handles pandas objects, datetimes and strips raw LLM blobs
    try:
        import pandas as pd
    except Exception:
        pd = None

    def safe(o, _seen=None):
        _seen = set() if _seen is None else _seen
        # Only track container types for circular references to avoid marking
        # duplicated primitive values (like strings) as circular.
        if isinstance(o, (dict, list, tuple, set)):
            oid = id(o)
            if oid in _seen:
                return "<circular>"
            _seen.add(oid)

        # primitives
        if o is None or isinstance(o, (str, int, float, bool)):
            return o
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if k == "raw":
                    # remove heavy/raw blobs from display
                    out[k] = "<raw omitted>"
                    continue
                try:
                    out[str(k)] = safe(v, _seen)
                except Exception:
                    out[str(k)] = str(v)
            return out
        if isinstance(o, (list, tuple)):
            return [safe(x, _seen) for x in o]
        try:
            from datetime import datetime

            if isinstance(o, datetime):
                return o.isoformat()
        except Exception:
            pass
        if pd is not None and isinstance(o, pd.DataFrame):
            df2 = o.reset_index()
            for col in df2.columns:
                try:
                    if pd.api.types.is_datetime64_any_dtype(df2[col]):
                        df2[col] = df2[col].astype(str)
                except Exception:
                    pass
            return df2.tail(5).to_dict(orient="records")
        # fallback to string
        try:
            json.dumps(o)
            return o
        except Exception:
            return str(o)

    safe_state = safe(state)
    return json.dumps(safe_state, ensure_ascii=False, indent=2)


def _print_step(step: dict[str, Any]) -> None:
    node_name = step.get("node_name", "Unknown")
    node_state = step.get("node_state", {}) or {}

    print(f"=== {node_name} ===")

    for label in ("thought", "action", "arguments", "route", "tool", "summary", "status", "errors"):
        value = node_state.get(label)
        if value:
            if label == "arguments" and isinstance(value, dict):
                print(f"ARGUMENTS: {json.dumps(value, ensure_ascii=False)}")
            elif label == "route" and isinstance(value, (list, tuple, set)):
                print(f"ROUTE: {', '.join(str(item) for item in value)}")
            else:
                print(f"{label.upper()}: {value}")

    if node_name == "Tổng Hợp":
        print("=== FINAL_REPORT ===")
        print(node_state.get("final_recommendation", ""))
        return

    return


def main(args=None):
    parser = argparse.ArgumentParser(description="Run Financial AI Agent Team Supervisor")
    parser.add_argument("--symbol", type=str, help="Stock symbol (e.g., HPG)")
    parser.add_argument("--start", type=str, default="2023-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, default="2023-02-01", help="End date YYYY-MM-DD")
    parser.add_argument("--query", type=str, default=None, help="Optional natural-language query")
    parser.add_argument("--mode", type=str, choices=["data", "news", "analysis", "all"], default="all")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive multi-turn mode with conversation memory")
    parser.add_argument("--session", type=str, default=None, help="Load conversation from session file")
    parser.add_argument("--save", action="store_true", help="Save conversation after completion")
    parsed_args = parser.parse_args(args)

    # Initialize supervisor with optional conversation memory
    conversation_memory = None
    if parsed_args.session and Path(parsed_args.session).exists():
        print(f"📂 Loading conversation from {parsed_args.session}...")
        conversation_memory = ConversationMemory.load_from_file(Path(parsed_args.session))
    
    sup = Supervisor(conversation_memory=conversation_memory)
    
    # Interactive mode
    if parsed_args.interactive:
        print("\n" + "="*80)
        print("🤖 FINANCIAL AI ADVISOR - INTERACTIVE MODE")
        print("="*80)
        print("📝 Type 'help' for commands, 'quit' to exit\n")
        
        _interactive_loop(sup, parsed_args)
    else:
        # Single query mode
        payload = {
            "query": parsed_args.query,
            "symbol": parsed_args.symbol,
            "start": parsed_args.start,
            "end": parsed_args.end,
            "mode": parsed_args.mode,
        }
        
        print("\n" + "="*80)
        print(f"📊 QUERY: {parsed_args.query or parsed_args.symbol or 'No query'}")
        print("="*80 + "\n")
        
        for step in sup.stream(payload):
            _print_step(step)
        
        if parsed_args.save:
            save_path = sup.save_conversation()
            print(f"\n✅ Conversation saved to: {save_path}")


def _interactive_loop(sup: Supervisor, args) -> None:
    """Interactive REPL loop with conversation memory."""
    commands = {
        "help": "Show this help message",
        "history": "Show conversation history",
        "clear": "Clear conversation history",
        "save": "Save conversation to file",
        "status": "Show current session info",
        "quit": "Exit the program",
    }
    
    try:
        while True:
            try:
                user_input = input("💬 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == "help":
                    print("\n📋 Available commands:")
                    for cmd, description in commands.items():
                        print(f"  • {cmd}: {description}")
                    print()
                    continue
                
                if user_input.lower() == "history":
                    print("\n" + sup.get_conversation_history())
                    print()
                    continue
                
                if user_input.lower() == "clear":
                    sup.clear_conversation()
                    print("✅ Conversation cleared. Starting fresh.\n")
                    continue
                
                if user_input.lower() == "save":
                    save_path = sup.save_conversation()
                    print(f"✅ Conversation saved to: {save_path}\n")
                    continue
                
                if user_input.lower() == "status":
                    memory = sup.get_conversation_memory()
                    print(f"\n📊 Session Status:")
                    print(f"  • Session ID: {memory.session_id}")
                    print(f"  • Total turns: {len(memory.turns) // 2}")
                    print(f"  • Tracked symbols: {memory.entities.get('all_symbols', [])}")
                    print()
                    continue
                
                if user_input.lower() == "quit":
                    print("\n👋 Goodbye!")
                    break
                
                # Process query with conversation memory
                print("🔄 Processing...\n")
                
                payload = {
                    "query": user_input,
                    "symbol": args.symbol or "",
                    "start": args.start,
                    "end": args.end,
                }
                
                final_response = None
                for step in sup.stream(payload, conversation_memory=sup.get_conversation_memory()):
                    if step["node_name"] == "final_report":
                        final_response = step["node_state"].get("final_recommendation")
                
                if final_response:
                    print(f"\n🤖 Agent: {final_response}\n")
                else:
                    print("⚠️ No response generated.\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Exiting...")
                break
    except EOFError:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()
