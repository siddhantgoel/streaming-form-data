"""Simple benchmark script for streaming-form-data parser (Sync & Async)."""

import asyncio
import time
from io import BytesIO
from statistics import mean, stdev

import psutil
from numpy import random
from requests_toolbelt import MultipartEncoder

from streaming_form_data.parser import StreamingFormDataParser, AsyncStreamingFormDataParser
from streaming_form_data.targets import NullTarget, AsyncNullTarget


class MemoryTracker:
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
    random.seed(int(time.time()))
    return random.bytes(size_mb * 1024 * 1024)


def create_multipart_data(file_data: bytes) -> tuple[bytes, str]:
    with BytesIO(file_data) as fd:
        encoder = MultipartEncoder(
            fields={"file": ("test.bin", fd, "application/octet-stream")}
        )
        return encoder.to_string(), encoder.content_type


def run_single_benchmark_sync(
    data: bytes, multipart_data: bytes, content_type: str, chunk_size: int
):
    parser = StreamingFormDataParser(headers={"Content-Type": content_type})
    parser.register("file", NullTarget())

    memory_tracker = MemoryTracker()
    memory_tracker.sample()

    start_time = time.perf_counter()
    position = 0

    while position < len(multipart_data):
        chunk_end = min(position + chunk_size, len(multipart_data))
        parser.data_received(multipart_data[position:chunk_end])
        position = chunk_end
        if position % (chunk_size * 100) == 0:
            memory_tracker.sample()

    end_time = time.perf_counter()
    memory_tracker.sample()

    parse_time = end_time - start_time
    throughput = (len(multipart_data) / parse_time) / (1024 * 1024)
    memory_increase = memory_tracker.get_memory_increase_mb()
    return throughput, memory_increase


def benchmark_sync(data, multipart_data, content_type, chunk_size, iterations):
    print("Synchronous Benchmark:")
    throughputs = []
    
    for i in range(iterations):
        throughput, _ = run_single_benchmark_sync(
            data, multipart_data, content_type, chunk_size
        )
        throughputs.append(throughput)
        print(f"  Iteration {i+1}: {throughput:.1f} MB/s")

    avg = mean(throughputs)
    std = stdev(throughputs) if len(throughputs) > 1 else 0
    print(f"Sync Result: {avg:.1f} ± {std:.1f} MB/s")
    return avg


async def run_single_benchmark_async(
    data: bytes, multipart_data: bytes, content_type: str, chunk_size: int
):
    parser = AsyncStreamingFormDataParser(headers={"Content-Type": content_type})
    parser.register("file", AsyncNullTarget())

    memory_tracker = MemoryTracker()
    memory_tracker.sample()

    start_time = time.perf_counter()
    position = 0

    while position < len(multipart_data):
        chunk_end = min(position + chunk_size, len(multipart_data))
        await parser.data_received(multipart_data[position:chunk_end])
        position = chunk_end
        if position % (chunk_size * 100) == 0:
            memory_tracker.sample()

    end_time = time.perf_counter()
    memory_tracker.sample()

    parse_time = end_time - start_time
    throughput = (len(multipart_data) / parse_time) / (1024 * 1024)
    memory_increase = memory_tracker.get_memory_increase_mb()
    return throughput, memory_increase


async def benchmark_async(data, multipart_data, content_type, chunk_size, iterations):
    print("Asynchronous Benchmark:")
    throughputs = []
    
    for i in range(iterations):
        throughput, _ = await run_single_benchmark_async(
            data, multipart_data, content_type, chunk_size
        )
        throughputs.append(throughput)
        print(f"  Iteration {i+1}: {throughput:.1f} MB/s")

    avg = mean(throughputs)
    std = stdev(throughputs) if len(throughputs) > 1 else 0
    print(f"Async Result: {avg:.1f} ± {std:.1f} MB/s")
    return avg


async def main(data_size_mb: int = 100, chunk_size: int = 131072, iterations: int = 30):
    print(f"Generating {data_size_mb}MB test data...")
    data = generate_test_data(data_size_mb)
    multipart_data, content_type = create_multipart_data(data)

    sync_result = benchmark_sync(data, multipart_data, content_type, chunk_size, iterations)
    async_result = await benchmark_async(data, multipart_data, content_type, chunk_size, iterations)

    diff = (sync_result - async_result) / sync_result * 100
    print(f"\nComparison: Async is {diff:.2f}% slower than Sync with {chunk_size}B chunks.")


if __name__ == "__main__":
    asyncio.run(main())