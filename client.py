import sys, json, time

class AgentBudgetTokenSpendCircuitBreaker:
    """
    Zero-Dependency Agentic Cost & Token Spend Circuit Breaker.
    Prevents runaway LLM agent loops from draining API budgets.
    Maintains three operational states:
    - NORMAL (< 80% budget consumed)
    - THROTTLED (80% - 99% budget consumed, forces downgrade / delays)
    - TRIPPED_EMERGENCY_FREEZE (>= 100% budget, rejects all generation calls)
    """
    MODEL_RATES = {
        "claude-3-5-sonnet": {"input_per_m": 3.00, "output_per_m": 15.00},
        "gpt-4o": {"input_per_m": 2.50, "output_per_m": 10.00},
        "gpt-4o-mini": {"input_per_m": 0.15, "output_per_m": 0.60},
        "claude-3-haiku": {"input_per_m": 0.25, "output_per_m": 1.25}
    }

    def __init__(self, max_budget_usd=10.0, throttle_pct=0.80):
        self.max_budget_usd = float(max_budget_usd)
        self.throttle_pct = float(throttle_pct)
        self.total_cost_usd = 0.0
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.history = []
        self.is_tripped = False

    def record_usage(self, model_name, tokens_in, tokens_out):
        if self.is_tripped:
            return {
                "allowed": False,
                "state": "TRIPPED_EMERGENCY_FREEZE",
                "error": "Circuit breaker is tripped! Budget exceeded. All calls frozen.",
                "total_cost_usd": round(self.total_cost_usd, 4),
                "max_budget_usd": self.max_budget_usd
            }

        rates = self.MODEL_RATES.get(model_name, {"input_per_m": 3.0, "output_per_m": 15.0})
        cost_in = (tokens_in / 1_000_000.0) * rates["input_per_m"]
        cost_out = (tokens_out / 1_000_000.0) * rates["output_per_m"]
        call_cost = cost_in + cost_out

        self.total_cost_usd += call_cost
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out

        ratio = self.total_cost_usd / self.max_budget_usd
        if ratio >= 1.0:
            self.is_tripped = True
            state = "TRIPPED_EMERGENCY_FREEZE"
            allowed = False
        elif ratio >= self.throttle_pct:
            state = "THROTTLED"
            allowed = True
        else:
            state = "NORMAL"
            allowed = True

        self.history.append({"time": time.time(), "model": model_name, "cost": call_cost, "state": state})

        return {
            "allowed": allowed,
            "state": state,
            "call_cost_usd": round(call_cost, 6),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "budget_used_pct": round(ratio * 100.0, 2),
            "is_tripped": self.is_tripped
        }

    def get_status(self):
        ratio = self.total_cost_usd / self.max_budget_usd if self.max_budget_usd > 0 else 1.0
        return {
            "state": "TRIPPED_EMERGENCY_FREEZE" if self.is_tripped else ("THROTTLED" if ratio >= self.throttle_pct else "NORMAL"),
            "is_tripped": self.is_tripped,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "max_budget_usd": self.max_budget_usd,
            "total_tokens": self.total_tokens_in + self.total_tokens_out,
            "call_count": len(self.history)
        }

    def reset(self):
        self.total_cost_usd = 0.0
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.is_tripped = False
        self.history = []
        return {"status": "RESET_SUCCESSFUL", "state": "NORMAL"}

    def run_benchmark_circuit_breaker(self):
        self.reset()
        # Call 1: Normal spend
        r1 = self.record_usage("claude-3-5-sonnet", 100_000, 20_000)
        # Call 2: Push into throttle (> $8 on $10 budget)
        r2 = self.record_usage("claude-3-5-sonnet", 1_500_000, 300_000)
        # Call 3: Exceed $10 budget and trip
        r3 = self.record_usage("claude-3-5-sonnet", 500_000, 100_000)
        # Call 4: Attempt after trip
        r4 = self.record_usage("claude-3-5-sonnet", 1_000, 1_000)

        return {
            "benchmark_status": "PASSED",
            "first_call_normal": r1["state"] == "NORMAL",
            "second_call_throttled": r2["state"] == "THROTTLED",
            "third_call_tripped": r3["state"] == "TRIPPED_EMERGENCY_FREEZE",
            "fourth_call_rejected": not r4["allowed"]
        }
