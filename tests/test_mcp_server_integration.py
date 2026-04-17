#!/usr/bin/env python
"""Test MCP server via stdio transport.

Sends JSON-RPC messages to the MCP server and verifies responses.
"""

import json
import subprocess
import sys
import time
import os
import select

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "repo_context.db")
SERVER_CMD = [
    sys.executable, "-m", "repo_context.cli.main", "serve-mcp",
    "--db-path", DB_PATH,
]

def send_message(proc, message: dict, timeout: float = 5.0) -> dict | None:
    """Send a JSON-RPC message to the MCP server and read the response."""
    # Write message to stdin
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()
    
    # Read response from stdout
    start = time.time()
    while time.time() - start < timeout:
        if select.select([proc.stdout], [], [], 0.1)[0]:
            line = proc.stdout.readline()
            if line.strip():
                return json.loads(line)
        time.sleep(0.05)
    return None

def test_mcp_server():
    """Test the MCP server with real JSON-RPC messages."""
    errors = []
    
    # Start server
    print("Starting MCP server...")
    proc = subprocess.Popen(
        SERVER_CMD,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    time.sleep(1)  # Let server start
    
    try:
        # Test 1: Initialize
        print("\n1. Testing initialize...")
        resp = send_message(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        })
        if resp and resp.get("result"):
            print("   ✅ Initialize OK")
        else:
            errors.append("Initialize failed")
            print(f"   ❌ Initialize failed: {resp}")
        
        # Test 2: List tools
        print("\n2. Testing tools/list...")
        resp = send_message(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })
        if resp and resp.get("result"):
            tools = resp["result"].get("tools", [])
            tool_names = [t["name"] for t in tools]
            expected = [
                "resolve_symbol_tool",
                "get_symbol_context_tool",
                "refresh_symbol_references_tool",
                "get_symbol_references_tool",
                "analyze_symbol_risk_tool",
                "analyze_target_set_risk_tool",
            ]
            for name in expected:
                if name in tool_names:
                    print(f"   ✅ Tool registered: {name}")
                else:
                    errors.append(f"Missing tool: {name}")
                    print(f"   ❌ Missing tool: {name}")
        else:
            errors.append("tools/list failed")
            print(f"   ❌ tools/list failed: {resp}")
        
        # Test 3: Call resolve_symbol_tool
        print("\n3. Testing resolve_symbol_tool...")
        resp = send_message(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "resolve_symbol_tool",
                "arguments": {
                    "repo_id": "repo:MCP_Server_Sandbox",
                    "qualified_name": "src.repo_context.context.builders.build_symbol_context",
                },
            },
        })
        if resp and resp.get("result"):
            content = resp["result"].get("content", [])
            if content:
                data = json.loads(content[0]["text"])
                if data.get("ok"):
                    print(f"   ✅ resolve_symbol OK: {data['data']['symbol']['id']}")
                else:
                    errors.append(f"resolve_symbol returned error: {data.get('error')}")
                    print(f"   ❌ resolve_symbol error: {data.get('error')}")
            else:
                errors.append("resolve_symbol returned no content")
                print(f"   ❌ resolve_symbol returned no content")
        else:
            errors.append("resolve_symbol call failed")
            print(f"   ❌ resolve_symbol call failed: {resp}")
        
        # Test 4: Call get_symbol_context_tool
        print("\n4. Testing get_symbol_context_tool...")
        resp = send_message(proc, {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_symbol_context_tool",
                "arguments": {
                    "symbol_id": "sym:repo:MCP_Server_Sandbox:function:src.repo_context.context.builders.build_symbol_context",
                },
            },
        })
        if resp and resp.get("result"):
            content = resp["result"].get("content", [])
            if content:
                data = json.loads(content[0]["text"])
                if data.get("ok"):
                    ctx = data["data"]["context"]
                    print(f"   ✅ get_symbol_context OK: {ctx['focus_symbol']['qualified_name']}")
                    print(f"      Children: {len(ctx['structural_children'])}")
                    print(f"      Incoming edges: {len(ctx['incoming_edges'])}")
                else:
                    errors.append(f"get_symbol_context returned error: {data.get('error')}")
                    print(f"   ❌ get_symbol_context error: {data.get('error')}")
            else:
                errors.append("get_symbol_context returned no content")
                print(f"   ❌ get_symbol_context returned no content")
        else:
            errors.append("get_symbol_context call failed")
            print(f"   ❌ get_symbol_context call failed: {resp}")
        
        # Test 5: Call analyze_symbol_risk_tool
        print("\n5. Testing analyze_symbol_risk_tool...")
        resp = send_message(proc, {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "analyze_symbol_risk_tool",
                "arguments": {
                    "symbol_id": "sym:repo:MCP_Server_Sandbox:function:src.repo_context.context.builders.build_symbol_context",
                },
            },
        })
        if resp and resp.get("result"):
            content = resp["result"].get("content", [])
            if content:
                data = json.loads(content[0]["text"])
                if data.get("ok"):
                    risk = data["data"]["risk"]
                    print(f"   ✅ analyze_symbol_risk OK: score={risk['risk_score']}, decision={risk['decision']}")
                    print(f"      Issues: {risk['issues']}")
                else:
                    errors.append(f"analyze_symbol_risk returned error: {data.get('error')}")
                    print(f"   ❌ analyze_symbol_risk error: {data.get('error')}")
            else:
                errors.append("analyze_symbol_risk returned no content")
                print(f"   ❌ analyze_symbol_risk returned no content")
        else:
            errors.append("analyze_symbol_risk call failed")
            print(f"   ❌ analyze_symbol_risk call failed: {resp}")
        
        # Test 6: Call get_symbol_references_tool
        print("\n6. Testing get_symbol_references_tool...")
        resp = send_message(proc, {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "get_symbol_references_tool",
                "arguments": {
                    "symbol_id": "sym:repo:MCP_Server_Sandbox:function:src.repo_context.context.builders.build_symbol_context",
                },
            },
        })
        if resp and resp.get("result"):
            content = resp["result"].get("content", [])
            if content:
                data = json.loads(content[0]["text"])
                if data.get("ok"):
                    refs = data["data"]["references"]
                    summary = data["data"]["reference_summary"]
                    print(f"   ✅ get_symbol_references OK: {len(refs)} references, available={summary['available']}")
                else:
                    errors.append(f"get_symbol_references returned error: {data.get('error')}")
                    print(f"   ❌ get_symbol_references error: {data.get('error')}")
            else:
                errors.append("get_symbol_references returned no content")
                print(f"   ❌ get_symbol_references returned no content")
        else:
            errors.append("get_symbol_references call failed")
            print(f"   ❌ get_symbol_references call failed: {resp}")
        
        # Test 7: Call analyze_target_set_risk_tool
        print("\n7. Testing analyze_target_set_risk_tool...")
        resp = send_message(proc, {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "analyze_target_set_risk_tool",
                "arguments": {
                    "symbol_ids": [
                        "sym:repo:MCP_Server_Sandbox:function:src.repo_context.context.builders.build_symbol_context",
                        "sym:repo:MCP_Server_Sandbox:function:src.repo_context.context.summaries.build_structural_summary",
                    ],
                },
            },
        })
        if resp and resp.get("result"):
            content = resp["result"].get("content", [])
            if content:
                data = json.loads(content[0]["text"])
                if data.get("ok"):
                    risk = data["data"]["risk"]
                    print(f"   ✅ analyze_target_set_risk OK: score={risk['risk_score']}, decision={risk['decision']}")
                    print(f"      Targets: {risk['facts']['target_count']}")
                else:
                    errors.append(f"analyze_target_set_risk returned error: {data.get('error')}")
                    print(f"   ❌ analyze_target_set_risk error: {data.get('error')}")
            else:
                errors.append("analyze_target_set_risk returned no content")
                print(f"   ❌ analyze_target_set_risk returned no content")
        else:
            errors.append("analyze_target_set_risk call failed")
            print(f"   ❌ analyze_target_set_risk call failed: {resp}")
        
        # Test 8: Test error handling - invalid input
        print("\n8. Testing error handling (invalid input)...")
        resp = send_message(proc, {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "resolve_symbol_tool",
                "arguments": {
                    "repo_id": "",
                    "qualified_name": "",
                },
            },
        })
        if resp and resp.get("result"):
            content = resp["result"].get("content", [])
            if content:
                data = json.loads(content[0]["text"])
                if not data.get("ok") and data.get("error", {}).get("code") == "invalid_input":
                    print(f"   ✅ Error handling OK: {data['error']['message']}")
                else:
                    errors.append(f"Error handling returned unexpected: {data}")
                    print(f"   ❌ Error handling unexpected: {data}")
            else:
                errors.append("Error handling returned no content")
                print(f"   ❌ Error handling returned no content")
        else:
            errors.append("Error handling call failed")
            print(f"   ❌ Error handling call failed: {resp}")
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    
    # Summary
    print("\n" + "=" * 60)
    assert not errors, f"Test failed with errors: {errors}"
    print("ALL TESTS PASSED ✅")


if __name__ == "__main__":
    test_mcp_server()
