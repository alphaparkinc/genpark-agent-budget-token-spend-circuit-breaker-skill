from client import AgentBudgetTokenSpendCircuitBreaker
import json

def main():
    breaker = AgentBudgetTokenSpendCircuitBreaker()
    res = breaker.run_benchmark_circuit_breaker()
    print("Budget Circuit Breaker Benchmark Result:")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
