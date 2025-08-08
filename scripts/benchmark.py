"""Simple benchmark script for streaming-form-data parser."""

import time
from io import BytesIO
from statistics import mean, stdev

import psutil
from numpy import random
from requests_toolbelt import MultipartEncoder

from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.targets import NullTarget


class MemoryTracker:
    """Tracks memory usage during parsing."""

    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
        self.peak_memory = self.initial_memory

    def sample(self):
        current = self.process.memory_info().rss
        self.peak_memory = max(self.peak_memory, current)
        return current

    def get_memory_increase_mb(self):
        return (self.peak_memory - self.initial_memory) / (1024 * 1024)


def generate_test_data(size_mb: int) -> bytes:
    """Generate random test data."""
    random.seed(int(time.time()))
    return random.bytes(size_mb * 1024 * 1024)


def create_multipart_data(file_data: bytes) -> tuple[bytes, str]:
    """Create multipart form data."""
    with BytesIO(file_data) as fd:
        encoder = MultipartEncoder(
            fields={"file": ("test.bin", fd, "application/octet-stream")}
        )
        return encoder.to_string(), encoder.content_type


def run_single_benchmark(
    data: bytes, multipart_data: bytes, content_type: str, chunk_size: int
):
    """Run a single benchmark iteration."""
    # Setup parser
    parser = StreamingFormDataParser(headers={"Content-Type": content_type})
    parser.register("file", NullTarget())

    # Track memory
    memory_tracker = MemoryTracker()
    memory_tracker.sample()

    # Parse data in chunks
    start_time = time.perf_counter()
    position = 0

    while position < len(multipart_data):
        chunk_end = min(position + chunk_size, len(multipart_data))
        parser.data_received(multipart_data[position:chunk_end])
        position = chunk_end

        # Sample memory periodically
        if position % (chunk_size * 100) == 0:
            memory_tracker.sample()

    end_time = time.perf_counter()
    memory_tracker.sample()

    # Calculate results
    parse_time = end_time - start_time
    throughput = (len(multipart_data) / parse_time) / (1024 * 1024)
    memory_increase = memory_tracker.get_memory_increase_mb()

    return throughput, memory_increase


def benchmark_parser(
    data_size_mb: int = 100, chunk_size: int = 1024, iterations: int = 5
):
    """Run benchmark with multiple iterations and statistics."""
    print(
        f"Benchmarking {data_size_mb}MB file with {chunk_size} byte chunks ({iterations} iterations)..."
    )

    # Generate test data once
    data = generate_test_data(data_size_mb)
    multipart_data, content_type = create_multipart_data(data)

    throughputs = []
    memory_increases = []

    # Run multiple iterations
    for i in range(iterations):
        throughput, memory_increase = run_single_benchmark(
            data, multipart_data, content_type, chunk_size
        )
        throughputs.append(throughput)
        memory_increases.append(memory_increase)
        print(
            f"  Iteration {i+1}: {throughput:.1f} MB/s, +{memory_increase:.1f}MB memory"
        )

    # Calculate statistics
    avg_throughput = mean(throughputs)
    std_throughput = stdev(throughputs) if len(throughputs) > 1 else 0
    avg_memory = mean(memory_increases)

    print("\nResults:")
    print(f"Throughput: {avg_throughput:.1f} ± {std_throughput:.1f} MB/s")
    print(f"Memory increase: {avg_memory:.1f} MB")
    print(f"Data processed: {len(multipart_data) / (1024 * 1024):.1f} MB")


if __name__ == "__main__":
    benchmark_parser()
