import sys, json
from client import AgentBudgetTokenSpendCircuitBreaker

def main():
    breaker = AgentBudgetTokenSpendCircuitBreaker()
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            req = json.loads(line)
            method = req.get("method")
            rid = req.get("id")
            params = req.get("params", {})

            if method == "tools/list":
                res = {
                    "tools": [
                        {"name": "record_usage", "description": "Record tokens and check circuit breaker.", "inputSchema": {"type": "object", "properties": {"model_name": {"type": "string"}, "tokens_in": {"type": "integer"}, "tokens_out": {"type": "integer"}}, "required": ["model_name", "tokens_in", "tokens_out"]}},
                        {"name": "get_status", "description": "Get circuit breaker status.", "inputSchema": {"type": "object"}},
                        {"name": "reset", "description": "Reset circuit breaker.", "inputSchema": {"type": "object"}},
                        {"name": "run_benchmark_circuit_breaker", "description": "Run benchmark.", "inputSchema": {"type": "object"}}
                    ]
                }
            elif method == "tools/call":
                tname = params.get("name")
                args = params.get("arguments", {})
                if tname == "record_usage":
                    out = breaker.record_usage(args.get("model_name", "claude-3-5-sonnet"), int(args.get("tokens_in", 0)), int(args.get("tokens_out", 0)))
                elif tname == "get_status":
                    out = breaker.get_status()
                elif tname == "reset":
                    out = breaker.reset()
                elif tname == "run_benchmark_circuit_breaker":
                    out = breaker.run_benchmark_circuit_breaker()
                else:
                    out = {"error": f"Unknown tool {tname}"}
                res = {"content": [{"type": "text", "text": json.dumps(out)}]}
            else:
                res = {"error": "Unsupported method"}
            print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": res}), flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}), flush=True)

if __name__ == "__main__":
    main()
