"""End-to-end test: spawn the MCP server as a subprocess and perform a real
MCP protocol handshake. This is the test the smoke test can't do, because the
smoke test uses a FakeMCP stub. This one uses the real FastMCP server.

What it verifies:
  - server.py starts up cleanly with the real FastMCP
  - The server responds to MCP `initialize`
  - `tools/list` returns exactly the 9 expected tools with descriptions
  - `tools/call` for `get_daily_briefing` returns valid content
  - The server shuts down cleanly on stdin close

Run from inside the demo directory after `pip install -r requirements.txt`:
    python e2e_test.py

This is what Claude Desktop will do to your server when it connects, in
miniature. If this passes, Claude Desktop will work too.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent.resolve()

GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"


def main() -> int:
    print(f"{CYAN}Spawning server: {sys.executable} {HERE / 'server.py'}{RESET}")
    proc = subprocess.Popen(
        [sys.executable, str(HERE / "server.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=str(HERE),
    )

    def send(message: dict) -> None:
        line = json.dumps(message) + "\n"
        assert proc.stdin is not None
        proc.stdin.write(line)
        proc.stdin.flush()

    def receive(timeout_seconds: float = 5.0) -> dict | None:
        # Simple line-by-line read with a deadline
        assert proc.stdout is not None
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            line = proc.stdout.readline()
            if line:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    print(f"{DIM}non-JSON line ignored: {line.strip()[:120]}{RESET}")
                    continue
            if proc.poll() is not None:
                return None
            time.sleep(0.05)
        return None

    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        if condition:
            print(f"  {GREEN}✓{RESET} {label}")
        else:
            print(f"  {RED}✗{RESET} {label}")
            failures.append(label)

    try:
        # ------------------------------------------------------------------
        # 1. initialize
        # ------------------------------------------------------------------
        print(f"\n{CYAN}1. initialize{RESET}")
        send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agentsnap-e2e-test", "version": "1.0"},
            },
        })
        init = receive(timeout_seconds=10.0)
        check(init is not None, "received initialize response")
        if init is None:
            print(f"  {DIM}server stderr (if any):{RESET}")
            assert proc.stderr is not None
            err = proc.stderr.read(2000)
            print(err)
            return 1

        check(init.get("id") == 1, "response id matches request id")
        server_info = (init.get("result") or {}).get("serverInfo") or {}
        check("name" in server_info, f"serverInfo.name present ({server_info.get('name')})")
        capabilities = (init.get("result") or {}).get("capabilities") or {}
        check("tools" in capabilities, "server advertises 'tools' capability")

        # initialized notification (required by spec)
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        # ------------------------------------------------------------------
        # 2. tools/list
        # ------------------------------------------------------------------
        print(f"\n{CYAN}2. tools/list{RESET}")
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tlist = receive()
        check(tlist is not None, "received tools/list response")
        if tlist is None:
            return 1
        tools = (tlist.get("result") or {}).get("tools") or []
        check(len(tools) == 9, f"exactly 9 tools registered (got {len(tools)})")

        expected = {
            "get_daily_briefing", "get_renewal_pipeline", "search_contact",
            "get_contact_full", "create_renewal_invoice", "confirm_action",
            "create_claim", "list_claims", "get_commission_status",
        }
        actual = {t["name"] for t in tools}
        check(actual == expected, "tool names match expected set")
        if actual != expected:
            print(f"     missing: {expected - actual}")
            print(f"     extra:   {actual - expected}")

        check(all(t.get("description") for t in tools), "all tools have descriptions")
        check(all(t.get("inputSchema") for t in tools), "all tools have inputSchema")

        print(f"  {DIM}Registered tools:{RESET}")
        for t in tools:
            desc = (t.get("description") or "").strip().split("\n")[0][:70]
            print(f"    {DIM}- {t['name']:<28} {desc}{RESET}")

        # ------------------------------------------------------------------
        # 3. tools/call — get_daily_briefing
        # ------------------------------------------------------------------
        print(f"\n{CYAN}3. tools/call get_daily_briefing{RESET}")
        send({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_daily_briefing", "arguments": {}},
        })
        call = receive()
        check(call is not None, "received tools/call response")
        if call is None:
            return 1

        result = call.get("result") or {}
        content = result.get("content") or []
        check(len(content) > 0, "result has content")

        text_block = next((c for c in content if c.get("type") == "text"), None)
        check(text_block is not None, "content includes a text block")

        if text_block is not None:
            try:
                data = json.loads(text_block["text"])
                check(isinstance(data, dict), "text content parses as JSON object")
                check("urgent_renewals_count" in data, "urgent_renewals_count present")
                check("next_action" in data, "next_action hint present")
                check(data.get("mode") in ("mock", "live"), "mode field is mock or live")
                print(f"  {DIM}mode={data.get('mode')}  "
                      f"urgent={data.get('urgent_renewals_count')}  "
                      f"overdue={data.get('overdue_invoices_count')}  "
                      f"claims={data.get('open_claims_count')}  "
                      f"commission_ytd=${data.get('commission_ytd')}{RESET}")
            except json.JSONDecodeError as e:
                check(False, f"text content is valid JSON ({e})")

        # ------------------------------------------------------------------
        # 4. tools/call — get_commission_status (verify the v1.1 seed bulk)
        # ------------------------------------------------------------------
        print(f"\n{CYAN}4. tools/call get_commission_status{RESET}")
        send({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "get_commission_status", "arguments": {}},
        })
        comm = receive()
        check(comm is not None, "received commission response")
        if comm is not None:
            content = (comm.get("result") or {}).get("content") or []
            text_block = next((c for c in content if c.get("type") == "text"), None)
            if text_block is not None:
                data = json.loads(text_block["text"])
                ytd = data.get("ytd_total", 0)
                carriers = data.get("by_carrier") or {}
                check(ytd > 4000, f"YTD commission > $4,000 (got ${ytd:.2f})")
                check(len(carriers) == 4, f"all 4 carriers represented (got {len(carriers)})")

        # ------------------------------------------------------------------
        # 5. Clean shutdown
        # ------------------------------------------------------------------
        print(f"\n{CYAN}5. shutdown{RESET}")
        assert proc.stdin is not None
        proc.stdin.close()
        try:
            proc.wait(timeout=5)
            check(True, "server exited cleanly on stdin close")
        except subprocess.TimeoutExpired:
            proc.kill()
            check(False, "server did not exit within 5 seconds of stdin close")

    finally:
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass

    # --------------------------------------------------------------------------
    # Final result
    # --------------------------------------------------------------------------
    print()
    if failures:
        print(f"{RED}✗ {len(failures)} end-to-end check(s) failed:{RESET}")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"{GREEN}✓ End-to-end MCP protocol test passed.{RESET}")
    print(f"{DIM}Claude Desktop should connect to this server without issues.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
