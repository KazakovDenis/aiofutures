# Aiofutures
![Python version](https://img.shields.io/badge/Python-3.8%2B-blue)
[![Tests](https://github.com/KazakovDenis/relatives/actions/workflows/cicd.yml/badge.svg)](https://github.com/KazakovDenis/aiofutures/actions/workflows/cicd.yml) 
![PyPI - Downloads](https://img.shields.io/pypi/dm/aiofutures)

- [General information](#general-information)
- [Installation](#installation)
- [Usage](#usage)
  - [Implicit initialization (global executor)](#implicit-initialization-global-executor)
  - [Explicit initialization](#explicit-initialization)
  - [UVLoop](#uvloop)
  - [Notes](#notes)
- [Contribution](#contribution)

## General information

`aiofutures` provides tools to integrate an asynchronous code into your synchronous 
application in a usual and easy way using standard library's `concurrent.futures.Executor` interface.  
  
It may be useful when you want to:
- smoothly migrate your synchronous codebase to asynchronous style
- decrease a number of threads in your application 

Replace this:
```python
from concurrent.futures import ThreadPoolExecutor

def sync_get_user(user_id):
    ...

with ThreadPoolExecutor() as ex:
    future = ex.submit(sync_get_user, user_id)
    result = future.result()
```

With this:
```python
from aiofutures import AsyncExecutor

async def async_get_user(user_id):
    ...

with AsyncExecutor() as ex:
    future = ex.submit(async_get_user, user_id)
    result = future.result()
```

**The former spawns a lot of threads and experiences all cons of GIL, the latter
spawns the only one async thread (check out [notes](#Notes))**. 

## Installation

You can install `aiofutures` using pip:

```
pip install aiofutures
```

## Usage

### Implicit initialization (global executor)

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

### Explicit initialization

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

NOTE: You can use `sync_to_async` within tasks running in the executor only.

### UVLoop

To use with the high performance `uvloop` install it before initialization:
```python
# install before the import for the global executor
import uvloop
uvloop.install()
from aiofutures import run_async
...

# or before an explicit initialization
import uvloop
from aiofutures import AsyncExecutor
uvloop.install()
executor = AsyncExecutor()
```

### Notes
- Take into account that asyncio still ([CPython3.13](https://github.com/python/cpython/blob/v3.13.0rc3/Lib/asyncio/base_events.py#L935))
resolves DNS in threads, not asynchronously
- Any blocking function will block the whole AsyncExecutor

## Contribution
All suggestions are welcome!
