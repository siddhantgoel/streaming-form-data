"""
Benchmark script comparing Sequential (Sync) vs Concurrent (Async) parsing
simulating network latency.

This demonstrates the advantage of Async when handling multiple concurrent
slow uploads (e.g., slow clients over the internet).
"""

import asyncio
import time
from io import BytesIO

from numpy import random
from requests_toolbelt import MultipartEncoder

from streaming_form_data import StreamingFormDataParser, AsyncStreamingFormDataParser
from streaming_form_data.targets import NullTarget, AsyncNullTarget

NUM_UPLOADS = 10         # Number of concurrent uploads
FILE_SIZE_MB = 1         # Size of each file
CHUNK_SIZE = 8192        # Chunk size (8KB)
SIMULATED_LATENCY = 0.001 # 1ms latency per chunk (simulating network)

def generate_multipart_data(size_mb: int) -> tuple[bytes, str]:
    """Generate a single multipart payload."""
    data = random.bytes(size_mb * 1024 * 1024)
    with BytesIO(data) as fd:
        encoder = MultipartEncoder(
            fields={"file": ("test.bin", fd, "application/octet-stream")}
        )
        return encoder.to_string(), encoder.content_type

def process_upload_sync(multipart_data, content_type, chunk_size, latency):
    parser = StreamingFormDataParser(headers={"Content-Type": content_type})
    parser.register("file", NullTarget())

    position = 0
    while position < len(multipart_data):
        # Simulate network latency (blocking)
        time.sleep(latency)
        
        chunk_end = min(position + chunk_size, len(multipart_data))
        parser.data_received(multipart_data[position:chunk_end])
        position = chunk_end

def benchmark_sync(payloads):
    print("Synchronous:")
    print(f"Processing {len(payloads)} uploads one by one...")
    
    start_time = time.perf_counter()
    
    for i, (data, content_type) in enumerate(payloads):
        process_upload_sync(data, content_type, CHUNK_SIZE, SIMULATED_LATENCY)
        
    duration = time.perf_counter() - start_time
    print(f"Total Time: {duration:.2f}s")
    return duration

async def process_upload_async(multipart_data, content_type, chunk_size, latency):
    parser = AsyncStreamingFormDataParser(headers={"Content-Type": content_type})
    parser.register("file", AsyncNullTarget())

    position = 0
    while position < len(multipart_data):
        # Simulate network latency (non-blocking)
        await asyncio.sleep(latency)
        
        chunk_end = min(position + chunk_size, len(multipart_data))
        await parser.data_received(multipart_data[position:chunk_end])
        position = chunk_end

async def benchmark_async(payloads):
    print("Asynchronous:")
    print(f"Processing {len(payloads)} uploads concurrently...")
    
    start_time = time.perf_counter()
    
    tasks = [
        process_upload_async(data, c_type, CHUNK_SIZE, SIMULATED_LATENCY)
        for data, c_type in payloads
    ]
    await asyncio.gather(*tasks)
    
    duration = time.perf_counter() - start_time
    print(f"Total Time: {duration:.2f}s")
    return duration

async def main():
    print(f"Generating {NUM_UPLOADS} test files ({FILE_SIZE_MB}MB each)...")
    payloads = [generate_multipart_data(FILE_SIZE_MB) for _ in range(NUM_UPLOADS)]
    
    print(f"\nSimulating {NUM_UPLOADS} clients uploading with {SIMULATED_LATENCY*1000}ms latency per chunk.")
    
    sync_time = benchmark_sync(payloads)
    async_time = await benchmark_async(payloads)
    
    speedup = sync_time / async_time
    print(f"\nResult: Async was {speedup:.1f}x faster")

if __name__ == "__main__":
    asyncio.run(main())