#!/usr/bin/env python3
"""
Comprehensive performance benchmark for streaming-form-data parser.
Measures throughput, memory usage, and provides detailed profiling.
"""

import argparse
import cProfile
import gc
import json
import pstats
import sys
import time
from io import BytesIO, StringIO
from statistics import mean, median, stdev

import psutil
from numpy import random
from requests_toolbelt import MultipartEncoder

from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.targets import BaseTarget, NullTarget


class BenchmarkTarget(BaseTarget):
    """Target that tracks performance metrics without storing data."""

    def __init__(self):
        self.bytes_received = 0
        self.chunks_received = 0
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.perf_counter()

    def data_received(self, chunk):
        self.bytes_received += len(chunk)
        self.chunks_received += 1

    def finish(self):
        self.end_time = time.perf_counter()


class MemoryTracker:
    """Tracks memory usage during parsing."""

    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
        self.peak_memory = self.initial_memory
        self.samples = []

    def sample(self):
        current = self.process.memory_info().rss
        self.peak_memory = max(self.peak_memory, current)
        self.samples.append(current)
        return current

    def get_stats(self):
        return {
            "initial_mb": self.initial_memory / 1024 / 1024,
            "peak_mb": self.peak_memory / 1024 / 1024,
            "increase_mb": (self.peak_memory - self.initial_memory) / 1024 / 1024,
            "samples": len(self.samples),
        }


def generate_test_data(size_mb: int, seed: int = 42) -> bytes:
    """Generate random test data of specified size."""
    random.seed(seed)
    return random.bytes(size_mb * 1024 * 1024)


def create_multipart_data(
    file_data: bytes, filename: str = "test.bin"
) -> tuple[bytes, str]:
    """Create multipart form data from file data."""
    with BytesIO(file_data) as fd:
        encoder = MultipartEncoder(
            fields={
                "file": (filename, fd, "application/octet-stream"),
                "name": "benchmark_test",
                "description": "Performance benchmark data",
            }
        )
        return encoder.to_string(), encoder.content_type


def run_benchmark(data: bytes, chunk_size: int, memory_tracker: MemoryTracker) -> dict:
    """Run a single benchmark with given parameters."""
    multipart_data, content_type = create_multipart_data(data)

    # Setup parser
    parser = StreamingFormDataParser(headers={"Content-Type": content_type})
    target = BenchmarkTarget()
    parser.register("file", target)
    parser.register("name", NullTarget())
    parser.register("description", NullTarget())

    # Measure parsing performance
    start_time = time.perf_counter()
    memory_tracker.sample()

    position = 0
    body_length = len(multipart_data)

    while position < body_length:
        chunk_end = min(position + chunk_size, body_length)
        chunk = multipart_data[position:chunk_end]
        parser.data_received(chunk)
        position = chunk_end

        # Sample memory every 100 chunks
        if (position // chunk_size) % 100 == 0:
            memory_tracker.sample()

    end_time = time.perf_counter()
    memory_tracker.sample()

    # Calculate metrics
    parse_time = end_time - start_time
    throughput_mbps = (body_length / parse_time) / (1024 * 1024)

    return {
        "parse_time": parse_time,
        "throughput_mbps": throughput_mbps,
        "body_size_mb": body_length / (1024 * 1024),
        "original_size_mb": len(data) / (1024 * 1024),
        "chunk_size": chunk_size,
        "chunks_processed": position // chunk_size,
        "target_bytes": target.bytes_received,
        "target_chunks": target.chunks_received,
    }


def profile_benchmark(data: bytes, chunk_size: int) -> str:
    """Run benchmark with cProfile and return stats."""
    multipart_data, content_type = create_multipart_data(data)

    def parse_data():
        parser = StreamingFormDataParser(headers={"Content-Type": content_type})
        target = NullTarget()
        parser.register("file", target)
        parser.register("name", NullTarget())
        parser.register("description", NullTarget())

        position = 0
        body_length = len(multipart_data)

        while position < body_length:
            chunk_end = min(position + chunk_size, body_length)
            chunk = multipart_data[position:chunk_end]
            parser.data_received(chunk)
            position = chunk_end

    # Profile the parsing
    profiler = cProfile.Profile()
    profiler.enable()
    parse_data()
    profiler.disable()

    # Get stats
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("tottime")
    stats.print_stats(20)

    return stream.getvalue()


def run_comprehensive_benchmark(args):
    """Run comprehensive benchmark suite."""
    print("=== Streaming Form Data Parser Benchmark ===\n")

    # Test configurations
    data_sizes = args.sizes or [1, 5, 10, 50, 100]  # MB
    chunk_sizes = args.chunks or [1024, 4096, 16384, 65536, 262144]  # bytes

    results = []

    for data_size in data_sizes:
        print(f"Testing with {data_size}MB data...")
        data = generate_test_data(data_size)

        for chunk_size in chunk_sizes:
            print(f"  Chunk size: {chunk_size} bytes", end=" ")

            # Run multiple iterations for statistical accuracy
            iterations = 3 if data_size <= 10 else 1
            iteration_results = []

            for i in range(iterations):
                gc.collect()  # Clean up before each run
                memory_tracker = MemoryTracker()

                result = run_benchmark(data, chunk_size, memory_tracker)
                result["memory"] = memory_tracker.get_stats()
                result["data_size_mb"] = data_size
                iteration_results.append(result)

            # Calculate statistics across iterations
            if len(iteration_results) > 1:
                throughputs = [r["throughput_mbps"] for r in iteration_results]
                avg_result = iteration_results[0].copy()
                avg_result.update(
                    {
                        "throughput_mbps": mean(throughputs),
                        "throughput_std": stdev(throughputs),
                        "throughput_median": median(throughputs),
                        "iterations": len(iteration_results),
                    }
                )
                results.append(avg_result)
                print(f"-> {mean(throughputs):.1f} ± {stdev(throughputs):.1f} MB/s")
            else:
                results.append(iteration_results[0])
                print(f"-> {iteration_results[0]['throughput_mbps']:.1f} MB/s")

    # Print summary
    print("\n=== Performance Summary ===")
    print(f"{'Data Size':<10} {'Chunk Size':<12} {'Throughput':<12} {'Memory':<10}")
    print("-" * 50)

    for result in results:
        data_mb = result["data_size_mb"]
        chunk_kb = result["chunk_size"] // 1024
        throughput = result["throughput_mbps"]
        memory_mb = result["memory"]["increase_mb"]

        print(
            f"{data_mb}MB{'':<6} {chunk_kb}KB{'':<8} {throughput:.1f} MB/s{'':<3} +{memory_mb:.1f}MB"
        )

    # Find optimal configurations
    best_throughput = max(results, key=lambda x: x["throughput_mbps"])
    print(f"\nBest throughput: {best_throughput['throughput_mbps']:.1f} MB/s")
    print(f"  Data size: {best_throughput['data_size_mb']}MB")
    print(f"  Chunk size: {best_throughput['chunk_size']} bytes")

    # Profile the best configuration
    if args.profile:
        print("\n=== Profiling Best Configuration ===")
        data = generate_test_data(best_throughput["data_size_mb"])
        profile_output = profile_benchmark(data, best_throughput["chunk_size"])
        print(profile_output)

    # Save results to JSON
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark streaming-form-data parser")
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        help="Data sizes to test in MB (default: 1,5,10,50,100)",
    )
    parser.add_argument(
        "--chunks",
        type=int,
        nargs="+",
        help="Chunk sizes to test in bytes (default: 1024,4096,16384,65536,262144)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run detailed profiling on best configuration",
    )
    parser.add_argument("--output", type=str, help="Save results to JSON file")

    args = parser.parse_args()

    try:
        run_comprehensive_benchmark(args)
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running benchmark: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
