# Async in Python Isn't Magic — It's Math: A Deep Dive for Real-World Developers
# Why Your FastAPI App Isn't Fast: Understanding Python Concurrency

## 🚦 Introduction: The Hidden Bottleneck

> "We ran a 500-user load test. FastAPI struggled. Turns out — someone used `requests` in an `async def`."
<!-- ### 📊 Real-World Load Test Results -->

Benchmarked the same FastAPI app with two minor differences: one used requests, the other used httpx. At 20 users, the difference was minor. At 200 users, one of them crumbled.

| Scenario       | Avg Resp. Time | Notes                     | Report |
|----------------|----------------|----------------------------|--------|
| Sync - 20 Users| ✅ Fast         | Comparable to async       | [View](https://www.akhil.pl/python-async-guide/sync-20-users.html) |
| Sync - 200 Users| ❌ Slow        | Response times spiked     | [View](https://www.akhil.pl/python-async-guide/sync-200-users.html) |
| Async - 20 Users| ✅ Fast        | Stable                    | [View](https://www.akhil.pl/python-async-guide/async-20-users.html) |
| Async - 200 Users| ✅ Fast       | Handled load gracefully   | [View](https://www.akhil.pl/python-async-guide/async-200-users.html) |
 

Even seasoned Python developers misuse asynchronous programming. The consequences? Poor scalability, mysterious performance drops, and sluggish APIs. This post will demystify Python's concurrency model, clarify common misconceptions, and provide practical tips to write scalable FastAPI applications.

What you'll learn:

- How Python threading, async, and multiprocessing really work
- When to use sync vs async
- How to avoid async anti-patterns that break your server under load

Too busy⏳ to read the entire post? Checkout the A TL;DR summary given after the conclusion. This post assumes that you have a basic understanding of the terms like Concurrency, Parallelism, GIL, Thread, Coroutine etc, and uses them mostly without any definition. If you have any confusion there is a Glossery session at the end where these terms are explained in details, please reffer that.

---

## 🔍 How Python Executes Code

To understand why your FastAPI app might feel sluggish, we need to look under the hood of Python’s execution model — especially how it handles concurrency and threads. When you run Python code, you might assume that multiple parts of it can run at the same time. After all, modern CPUs have multiple cores, and we often hear terms like threads, async, and parallelism. But here’s the twist: `By default, Python doesn't do true parallelism — even if you use threads.` That’s because of something called the Global Interpreter Lock (GIL) - The Gatekeeper of Python. So What Actually Happens When You Run Python Code? Here's a simplified sequence:
1. Your code is compiled into bytecode.
2. The Python interpreter (CPython) reads and executes the bytecode line by line.
3. Each line runs on a single thread.
4. The GIL ensures that only one thread runs at a time.
5. If there's a blocking operation (like time.sleep() or requests.get()), the thread pauses — and your app can feel painfully slow.

This becomes a problem in web apps. Imagine a FastAPI server receiving multiple requests at the same time. If each request is handled sequentially, request #2 will only start after all lines of request #1 are executed. That’s far from fast.

### 🧵 Enter Threading: A Partial Solution
To improve responsiveness, you might try using threads, where each request is handled in a separate thread. Then Python can run a little bit of each thread one after another, switching between them. But here's the catch: the GIL still controls everything. Even with multiple threads, only one can execute Python code at a time. So if one thread is doing CPU-heavy work (like image processing or looping over data), the other threads just have to wait. 

Eventhough python uses cooperative time-slicing to allow each thread to acquire the GIL only to run for a specific interval, a blocking task can make that time go wasted.

Still confused, let me paint a picture for you. Imagine a kitchen: You have one chef (the GIL), and multiple helpers (threads). Only one person can use the stove (CPU) at a time. If a helper is waiting for the storekeeper to bring ingredients (e.g., waiting on I/O), the chef allows another helper to use the stove. But if someone is constantly flipping pancakes (CPU-bound), no one else gets a chance to cook. So unless you organize your kitchen well, you’ll end up with delays, cold dishes, and frustrated helpers. That’s your FastAPI app when you misuse threads or ignore async features.

## ⚙️ How a FastAPI Application Runs

Now that you understand how Python executes code — and the bottleneck caused by the GIL — let’s zoom into how a FastAPI app actually works under the hood. FastAPI is designed for speed, but only when used correctly. It leverages modern Python features like async/await and runs on top of ASGI (Asynchronous Server Gateway Interface) — the asynchronous evolution of WSGI (used in synchronous frameworks like Flask and Django).

### 🚀 What Makes ASGI Special?
ASGI allows your FastAPI application to:
- Handle multiple requests concurrently without blocking.
- Support WebSockets and long-lived connections (unlike WSGI).
- Enable real-time communication (e.g., live chats, streaming APIs).
- Be highly scalable, especially when I/O-bound operations are optimized.

### 🛠️ What Happens When You Run a FastAPI App?
When you start your FastAPI app using:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
 Here's what happens behind the scenes:
1. Uvicorn, an ASGI web server, starts and runs the FastAPI app inside an ASGI event loop.
2. FastAPI, built on Starlette, determines how each route handler should be dispatched:
    - If the route is defined with `async def`: it’s scheduled on the event loop (main thread).
    - If the route is defined with `def`: Starlette uses `run_in_threadpool()` to move the function into a ThreadPoolExecutor.
        + This executor manages a finite pool of worker threads (often capped at 100 by default).
        + If all threads are busy, incoming sync requests must wait in a queue until a thread becomes available.
3. So at runtime, your application has:
    - A main thread running the event loop (for async work).
    - A pool of worker threads (for blocking sync work).

Python uses cooperative multitasking (via the asyncio event loop) for async code and preemptive time slicing for threads. So far, we've mostly explained how sync functions are handled — even though FastAPI is designed to be async-first. To truly unlock FastAPI’s performance, we now need to look at how async functions behave on the event loop — and how they enable non-blocking concurrency at scale.

## 🔄 The Async Magic: How FastAPI Handles `async def` Endpoints
Now that we’ve seen how FastAPI handles `def` routes using a thread pool, let’s explore the true power of FastAPI — non-blocking concurrency through `async def`.

### 🧠 Understanding the Event Loop
At the heart of all asynchronous execution in Python is the event loop, provided by the asyncio library. Think of the event loop as a manager that keeps track of tasks (coroutines), and runs them cooperatively, pausing one when it’s waiting on something (like I/O), and running another that’s ready. This allows your app to handle many requests at once, even with a single thread. You’ve already seen that `async def` route handlers are scheduled on the event loop. Here’s how they behave:
1. In the event loop, coroutines are executed sequentially, one step at a time.
2. When execution hits an `await` (usually an I/O operation):
    - The coroutine pauses and yields control.
    - The event loop switches to another coroutine — possibly handling another incoming request.
3. Once the awaited operation completes, the original coroutine resumes from where it left off.
4. Finally, it returns the result to the caller and the response is sent.

This dance of pausing and resuming enables massive concurrency without spawning new threads.

### 🧪 Async vs Sync Side-by-Side
Here is acomparison between Asyc
| Feature | `def` (Sync) | `async def` (Async) |
|----------|----------|----------|
| Execution model  | Thread in a thread pool  |  Coroutine in event loop  |
| Blocking behavior  | Blocks thread  |  Non-blocking, yields control on `await`  |
| Concurrency  | Limited by thread count  |  Thousands of concurrent I/O-bound requests  |
| Resource usage  | Higher (more threads = more memory)  |  Lower (single thread handles many tasks)  |
| Ideal use case  | Short CPU-bound or legacy code  |  Database calls, file I/O, external API requests  |


### 📈 Why This Matters for Performance
Let’s revisit the example: say 100 clients hit your FastAPI server.
- With sync endpoints: 100 requests = 100 threads = possible thread exhaustion.
- With async endpoints: 100 coroutines run efficiently in a single thread, managed by the event loop.

That’s a huge performance gain for I/O-bound workloads like: Reading from a database, Calling external APIs, Waiting on Redis/cache reads, file reads, etc. So it's settled, right? Make every router `async def` and your FastAPI app will be superfast, even under load?
> Well... not quite. 😄

Stay tuned — in the next section, we’ll look at the caveats of using async (like accidentally blocking the event loop), and how to do it right.

## 🚫 When async Isn't Enough: Common Pitfalls in Async FastAPI Apps
So far, we’ve seen how `async def` endpoints and the event loop enable FastAPI to handle thousands of requests concurrently — especially for I/O-bound operations. But just adding async to your route doesn’t automatically make it non-blocking or efficient. In fact, you can still block the event loop — and kill performance — if you’re not careful.

### ⚠️ Problem: Blocking Calls Inside async def
Take a look at this innocent-looking route:
```python
@app.get("/slow")
async def slow():
    response = requests.get("https://api.example.com/data")  # Blocking!
    return {"data": response.json()}
```
Looks fine, right? But this line: `requests.get(...)` is from the `requests` library — a synchronous function. It blocks the thread while waiting for a response. And since you’re inside an async def, this code is running on the event loop thread, which means: You’ve just blocked the entire event loop. -> No other coroutines can run until the blocking call finishes. -> Your “fast” app just became slow again.

#### ✅ Solution: Use Async-Compatible Libraries
To keep the event loop non-blocking, make sure you `await` non-blocking async functions. That means using async-compatible libraries. Below is a list of blocking and non blocking libraries for various use cases.

| Use Case	| Bad (Blocking)	| Good (Non-blocking) |
|----------|----------|----------|
| HTTP requests	| requests	| httpx.AsyncClient |
| DB access	| psycopg2	| asyncpg, databases |
| File I/O	| open(), read()	| aiofiles |
| Redis	| redis-py	| aioredis |
| Sleeping	| time.sleep()	| await asyncio.sleep() |

### ❌ Problem: CPU-Bound Tasks in Async Endpoints
Here’s another common mistake:
```python
@app.get("/compute")
async def compute():
    result = complex_calculation()  # Heavy CPU-bound work
    return {"result": result}
```
Even if this is inside an async def, a CPU-heavy task (like parsing large JSON, resizing images, or ML inference) will: Run on the event loop thread (since complex_calculation() is sync) -> Block all other coroutines from running -> And ultimately freeze your app under load.

#### ✅ Solution: Offload CPU Work to Threads or Processes
Use one of these options:
1. ThreadPoolExecutor for lightweight CPU-bound tasks (Trade-off: now you're using a thread per request, which limits scalability.):
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

@app.get("/compute")
async def compute():
    result = await asyncio.get_event_loop().run_in_executor(executor, complex_calculation)
    return {"result": result}
```
2. BackgroundTasks (for non-blocking post-response work).
3. Celery / RQ (for distributed, scalable background jobs).
4. ProcessPoolExecutor (for true CPU parallelism).

### 🧵 Pitfall: Running Independent Async Tasks Sequentially
Another common mistake in async FastAPI apps is running multiple independent await calls in sequence, instead of letting them run concurrently. Let’s say you’re fetching data from three different APIs:
```python
@app.get("/sequential")
async def sequential():
    res1 = await fetch_api_1()
    res2 = await fetch_api_2()
    res3 = await fetch_api_3()
    return {"res1": res1, "res2": res2, "res3": res3}
```
As python executes codes sequentially, Each call here waits for the previous one to finish. Even though all functions are async, you're effectively serializing them. What’s the problem? If each call takes 1 second, the total time becomes 3 seconds. That's not true concurrency.

#### ✅ Solution: Run Coroutines Concurrently with asyncio.gather
If your `await` calls are independent — don’t write them in sequence. Use `asyncio.gather()` to run them concurrently and speed things up. To run these tasks concurrently:
```python
@app.get("/concurrent")
async def concurrent():
    res1, res2, res3 = await asyncio.gather(
        fetch_api_1(),
        fetch_api_2(),
        fetch_api_3()
    )
    return {"res1": res1, "res2": res2, "res3": res3}
```
Here all three coroutines are scheduled at the same time. Total time ≈ the time taken by the slowest one, not the sum.

















## ✅ Conclusion: Making FastAPI Truly Fast
FastAPI is built for speed — but getting that speed in real-world applications isn’t automatic. It requires you to understand Python’s concurrency model, and to write your endpoints with care. Python's GIL limits true parallelism, so FastAPI relies on async/await and the ASGI event loop for efficient concurrency. def routes are pushed to a limited thread pool, while async def routes shine when used with non-blocking I/O. But misuse — like calling sync functions in async code or handling CPU-heavy tasks without offloading — can kill performance.

> 🧪 The Rule of Thumb? 
> Use async def for I/O-bound tasks with proper await-based libraries.
> Offload CPU-bound work to threads, processes, or background workers.

By understanding how FastAPI works under the hood — and how Python handles concurrency — you can build APIs that stay fast under load, remain responsive, and scale cleanly.

---

## 📚 Appendix: Glossary

### 🧠 Core Concepts
- **Concurrency:**  *The ability of a system to handle multiple tasks at once, by switching between them.*
    + Tasks start, pause, and resume — not necessarily finish at the same time.
    + In Python, asyncio and threading are tools for concurrency.
    + Think: Juggling multiple balls, one at a time.

- **Parallelism:** *The ability to perform multiple tasks simultaneously, usually on multiple CPU cores.*
    + True parallelism needs multiple threads or processes running on different cores.
    + Python threads don't do true parallelism due to the GIL.
    + Think: Multiple jugglers juggling simultaneously.

- **Multiprocessing:** *Running multiple independent processes, each with its own Python interpreter and memory.*
    + Used for CPU-bound tasks.
    + Not affected by the GIL — each process has its own.
    + Achieves real parallelism on multiple cores.
    + Python: multiprocessing module, ProcessPoolExecutor.

### 🔄 Thread-Based Terms
- **Thread:** *A lightweight unit of execution within a process.*
    + Threads share the same memory space.
    + In Python, multiple threads are limited by the GIL.
    + Best for I/O-bound work with blocking libraries.

- **ThreadPool / ThreadPoolExecutor:** *A pool of worker threads reused to perform tasks concurrently.*
    + Avoids overhead of constantly creating/destroying threads.
    + Used by FastAPI/Starlette to run def routes without blocking the event loop.

- **GIL (Global Interpreter Lock):** *A mutex in CPython that ensures only one thread executes Python bytecode at a time.*
    + Prevents race conditions.
    + Blocks true multithreaded parallelism.
    + Released temporarily during I/O or C extensions.

### ⚙️ Async Concepts
- **Asyncio:** *Python’s built-in library for writing asynchronous code using the async/await syntax.*
    + Uses an event loop to manage coroutines.
    + Enables efficient I/O-bound concurrency.

- **Coroutine:** *A special kind of function that can be paused and resumed (async def).*
    + Awaitable: can be used with await.
    + Gives control back to the event loop while waiting (non-blocking).
    ```python
    import asyncio

    async def my_coroutine():
        await asyncio.sleep(1)
    ```

- **Await:** *A keyword used to pause a coroutine until another coroutine or task completes.*
    + Lets the event loop continue with other tasks.
    + Only valid inside async def.

- **Event Loop:** *The scheduler that runs coroutines and coordinates asynchronous execution.*
    + Runs in the main thread in most asyncio programs.
    + Picks up coroutines when they’re ready to run, and resumes them after they await.

- **Task:** *A coroutine that has been scheduled to run by the event loop.*
    + Created via asyncio.create_task().
    + Allows multiple coroutines to run concurrently.
    ```python
    task = asyncio.create_task(my_coroutine())
    ```
- **Future:** *A low-level awaitable that represents a result that will be available in the future.*
    + Used internally by asyncio.
    + You usually use await on tasks or coroutines, not Futures directly.

- **Run in Executor:** *A method for running a blocking function in a separate thread or process from within async def.*
    ```python
    await asyncio.get_running_loop().run_in_executor(None, blocking_func)
    ```
    + Keeps the event loop responsive.

- **Blocking vs Non-Blocking:**
    | Term | Meaning |
    |----------|----------|
    | Blocking  | Halts program execution until operation completes (e.g. time.sleep)  |
    | Non-blocking  | Allows execution to continue while waiting (e.g. await asyncio.sleep)  |

- **I/O-Bound vs CPU-Bound:**
    | Type | Description | Best Tool |
    |----------|----------|----------|
    | I/O-bound  | Waits on external systems (network, disk)  |  asyncio, threads  |
    | CPU-bound  | Spends time on computation  |  multiprocessing  |

### 🧠 Summary Flow
```
User request ➝ FastAPI ➝
    ├── async def ➝ event loop ➝ coroutine ➝ await ➝ back to loop ➝ done ✅
    └── def ➝ thread pool ➝ blocking function ➝ done ✅ (but slower under load)
```

---

Would love your thoughts, corrections, or contributions. If this helped, share it with your team and help them avoid performance traps too!

