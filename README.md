# Aiofutures
[![Tests](https://github.com/KazakovDenis/relatives/actions/workflows/cicd.yml/badge.svg)](https://github.com/KazakovDenis/relatives/actions/workflows/cicd.yml)  

`aiofutures` provides tools to integrate an asynchronous code into your synchronous 
application in a usual and easy way using standard library's `concurrent.futures.Executor` interface.  
  
It may be useful when you want to:
- smoothly migrate your synchronous codebase to asynchronous style
- decrease a number of threads in your application 

Replace this:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor() as ex:
    future = ex.submit(sync_task)
    result = future.result()
```

With this:
```python
from aiofutures import AsyncExecutor

with AsyncExecutor() as ex:
    future = ex.submit(async_task)
    result = future.result()
```


## Installation

You can install `aiofutures` using pip:

```
pip install aiofutures
```

## Usage

### Simple way

Set an environment variable `AIOFUTURES_INIT` to any value and use shortcuts from the library:

```python
os.environ.setdefault('AIOFUTURES_INIT', '1')

from aiofutures import run_async

async def io_bound_task(seconds):
    await asyncio.sleep(seconds)
    return seconds

future = run_async(io_bound_task, 5)
print(future.result())
```
`AIOFUTURES_INIT` implicitly initializes a global `AsyncExecutor` and gives you an option to use 
shortcuts `run_async` and `sync_to_async`.

### Another way

Use an instance of the `AsyncExecutor` directly:

```python
from aiofutures import AsyncExecutor

executor = AsyncExecutor()
future = executor.submit(io_bound_task, 5)
print(future.result())
```

In cases when you need to do IO synchronously within async tasks, you can use `sync_to_async`:

```python
from aiofutures import AsyncExecutor, sync_to_async

executor = AsyncExecutor()

async def io_bound_task():
    # or with the shortcut
    # url = await sync_to_async(fetch_url_from_db_sync)
    url = await executor.sync_to_async(fetch_url_from_db_sync)
    data = await fetch_data(url)
    return data

future = executor.submit(io_bound_task)
print(future.result())
```

## Contribution
All suggestions are welcome!
