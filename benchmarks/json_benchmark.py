#!/usr/bin/env python3
"""
Benchmark comparing stdlib json vs orjson performance.

Run with: python benchmarks/json_benchmark.py

Requires: pip install orjson
"""

import json
import statistics
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

# Try to import orjson
try:
    import orjson

    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False
    print("orjson not installed. Install with: pip install orjson")
    print("Running stdlib json benchmarks only.\n")


# Custom UUID encoder for stdlib json
class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID objects."""

    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def generate_websocket_request() -> dict:
    """Generate a typical WebSocket request payload."""
    return {
        "pkg_id": 1,
        "req_id": uuid4(),
        "data": {
            "filters": {
                "status": "active",
                "created_after": datetime.now(UTC),
            },
            "page": 1,
            "per_page": 20,
        },
    }


def generate_websocket_response() -> dict:
    """Generate a typical WebSocket response payload."""
    return {
        "pkg_id": 1,
        "req_id": uuid4(),
        "status_code": 0,
        "data": {
            "items": [
                {
                    "id": i,
                    "name": f"Author {i}",
                    "email": f"author{i}@example.com",
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                    "metadata": {
                        "books_count": i * 10,
                        "rating": 4.5,
                        "tags": ["fiction", "bestseller", "award-winner"],
                    },
                }
                for i in range(20)
            ],
            "total": 100,
            "page": 1,
            "pages": 5,
        },
        "meta": {
            "total": 100,
            "page": 1,
            "per_page": 20,
            "pages": 5,
        },
    }


def generate_audit_log() -> dict:
    """Generate a typical audit log entry."""
    return {
        "timestamp": datetime.now(UTC),
        "user_id": str(uuid4()),
        "username": "test_user",
        "user_roles": ["admin", "editor", "viewer"],
        "action_type": "POST",
        "resource": "/api/authors",
        "outcome": "success",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "request_id": str(uuid4()),
        "request_data": {
            "name": "New Author",
            "email": "new@example.com",
            "bio": "A" * 500,  # Longer text field
        },
        "response_status": 201,
        "duration_ms": 45,
    }


def generate_broadcast_message() -> dict:
    """Generate a typical broadcast message."""
    return {
        "type": "broadcast",
        "channel": "notifications",
        "payload": {
            "event": "new_message",
            "data": {
                "id": uuid4(),
                "sender": "system",
                "content": "This is a notification message",
                "timestamp": datetime.now(UTC),
                "priority": "high",
            },
        },
    }


def benchmark_serialization(
    name: str, data: dict, iterations: int = 10000
) -> dict:
    """Benchmark JSON serialization."""
    results = {"name": name, "iterations": iterations}

    # Stdlib json with custom encoder
    times_json = []
    for _ in range(iterations):
        start = time.perf_counter()
        json.dumps(data, cls=UUIDEncoder)
        times_json.append((time.perf_counter() - start) * 1_000_000)  # µs

    results["json_mean_us"] = statistics.mean(times_json)
    results["json_median_us"] = statistics.median(times_json)
    results["json_stdev_us"] = statistics.stdev(times_json)

    if ORJSON_AVAILABLE:
        # orjson with native UUID/datetime support
        times_orjson = []
        for _ in range(iterations):
            start = time.perf_counter()
            orjson.dumps(
                data,
                option=orjson.OPT_SERIALIZE_UUID | orjson.OPT_UTC_Z,
            )
            times_orjson.append(
                (time.perf_counter() - start) * 1_000_000
            )  # µs

        results["orjson_mean_us"] = statistics.mean(times_orjson)
        results["orjson_median_us"] = statistics.median(times_orjson)
        results["orjson_stdev_us"] = statistics.stdev(times_orjson)
        results["speedup"] = (
            results["json_mean_us"] / results["orjson_mean_us"]
        )

    return results


def benchmark_deserialization(
    name: str, data: dict, iterations: int = 10000
) -> dict:
    """Benchmark JSON deserialization."""
    results = {"name": name, "iterations": iterations}

    # Serialize first
    json_str = json.dumps(data, cls=UUIDEncoder)
    json_bytes = json_str.encode("utf-8")

    # Stdlib json
    times_json = []
    for _ in range(iterations):
        start = time.perf_counter()
        json.loads(json_str)
        times_json.append((time.perf_counter() - start) * 1_000_000)  # µs

    results["json_mean_us"] = statistics.mean(times_json)
    results["json_median_us"] = statistics.median(times_json)
    results["json_stdev_us"] = statistics.stdev(times_json)

    if ORJSON_AVAILABLE:
        # orjson
        times_orjson = []
        for _ in range(iterations):
            start = time.perf_counter()
            orjson.loads(json_bytes)
            times_orjson.append(
                (time.perf_counter() - start) * 1_000_000
            )  # µs

        results["orjson_mean_us"] = statistics.mean(times_orjson)
        results["orjson_median_us"] = statistics.median(times_orjson)
        results["orjson_stdev_us"] = statistics.stdev(times_orjson)
        results["speedup"] = (
            results["json_mean_us"] / results["orjson_mean_us"]
        )

    return results


def benchmark_message_size(name: str, data: dict) -> dict:
    """Compare serialized message sizes."""
    results = {"name": name}

    json_str = json.dumps(data, cls=UUIDEncoder)
    results["json_size_bytes"] = len(json_str.encode("utf-8"))

    if ORJSON_AVAILABLE:
        orjson_bytes = orjson.dumps(
            data,
            option=orjson.OPT_SERIALIZE_UUID | orjson.OPT_UTC_Z,
        )
        results["orjson_size_bytes"] = len(orjson_bytes)
        results["size_diff_bytes"] = (
            results["json_size_bytes"] - results["orjson_size_bytes"]
        )
        results["size_reduction_pct"] = (
            results["size_diff_bytes"] / results["json_size_bytes"] * 100
        )

    return results


def print_results(title: str, results: list[dict]) -> None:
    """Print benchmark results in a table."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print("=" * 70)

    if ORJSON_AVAILABLE:
        print(
            f"{'Payload':<25} {'json (µs)':<12} {'orjson (µs)':<12} {'Speedup':<10}"
        )
        print("-" * 70)
        for r in results:
            print(
                f"{r['name']:<25} "
                f"{r['json_mean_us']:>10.2f}  "
                f"{r['orjson_mean_us']:>10.2f}  "
                f"{r['speedup']:>8.2f}x"
            )
    else:
        print(f"{'Payload':<25} {'json (µs)':<12}")
        print("-" * 50)
        for r in results:
            print(f"{r['name']:<25} {r['json_mean_us']:>10.2f}")


def print_size_results(results: list[dict]) -> None:
    """Print message size comparison."""
    print(f"\n{'=' * 70}")
    print(" Message Size Comparison")
    print("=" * 70)

    if ORJSON_AVAILABLE:
        print(f"{'Payload':<25} {'json':<12} {'orjson':<12} {'Diff':<10}")
        print("-" * 70)
        for r in results:
            diff = r.get("size_diff_bytes", 0)
            diff_str = f"{diff:+d}" if diff != 0 else "0"
            print(
                f"{r['name']:<25} "
                f"{r['json_size_bytes']:>10} B "
                f"{r.get('orjson_size_bytes', 'N/A'):>10} B "
                f"{diff_str:>8} B"
            )
    else:
        print(f"{'Payload':<25} {'json':<12}")
        print("-" * 50)
        for r in results:
            print(f"{r['name']:<25} {r['json_size_bytes']:>10} B")


def main() -> None:
    """Run all benchmarks."""
    print("JSON Serialization Benchmark")
    print("=" * 70)
    print(f"orjson available: {ORJSON_AVAILABLE}")

    # Generate test data
    payloads = {
        "WebSocket Request": generate_websocket_request(),
        "WebSocket Response": generate_websocket_response(),
        "Audit Log": generate_audit_log(),
        "Broadcast Message": generate_broadcast_message(),
    }

    # Serialization benchmarks
    serialize_results = []
    for name, data in payloads.items():
        result = benchmark_serialization(name, data)
        serialize_results.append(result)

    print_results("Serialization (dumps)", serialize_results)

    # Deserialization benchmarks
    deserialize_results = []
    for name, data in payloads.items():
        result = benchmark_deserialization(name, data)
        deserialize_results.append(result)

    print_results("Deserialization (loads)", deserialize_results)

    # Message size comparison
    size_results = []
    for name, data in payloads.items():
        result = benchmark_message_size(name, data)
        size_results.append(result)

    print_size_results(size_results)

    # Summary
    if ORJSON_AVAILABLE:
        avg_serialize_speedup = statistics.mean(
            r["speedup"] for r in serialize_results
        )
        avg_deserialize_speedup = statistics.mean(
            r["speedup"] for r in deserialize_results
        )

        print(f"\n{'=' * 70}")
        print(" Summary")
        print("=" * 70)
        print(f"Average serialization speedup:   {avg_serialize_speedup:.2f}x")
        print(
            f"Average deserialization speedup: {avg_deserialize_speedup:.2f}x"
        )
        print(
            f"Combined average speedup:        "
            f"{(avg_serialize_speedup + avg_deserialize_speedup) / 2:.2f}x"
        )

        # Estimate impact for WebSocket scenarios
        print(f"\n{'=' * 70}")
        print(" Estimated Impact (WebSocket Broadcast)")
        print("=" * 70)

        # Get WebSocket response benchmark
        ws_response = next(
            r for r in serialize_results if r["name"] == "WebSocket Response"
        )
        json_time = ws_response["json_mean_us"]
        orjson_time = ws_response["orjson_mean_us"]

        for num_clients in [100, 500, 1000]:
            json_total = json_time * num_clients / 1000  # ms
            orjson_total = orjson_time * num_clients / 1000  # ms
            saved = json_total - orjson_total

            print(
                f"{num_clients:4d} clients: "
                f"json={json_total:7.2f}ms, "
                f"orjson={orjson_total:7.2f}ms, "
                f"saved={saved:7.2f}ms"
            )


if __name__ == "__main__":
    main()
