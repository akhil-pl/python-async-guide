[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/akhil-pl/python-async-guide/blob/main/notebooks/concurrency_demo.ipynb)
 
# Python Async Guide Companion Repository

This repository accompanies the blog post: **"Async in Python Isn't Magic — It's Math"**.

It includes live examples, load test scripts, and Jupyter notebooks to help you experiment with Python's async, threading, and multiprocessing capabilities.

## 📦 Requirements

```bash
pip install -r requirements.txt
```

## 🚀 Running Examples

### 1. Run Async vs Sync FastAPI
```bash
# Sync app (uses requests)
uvicorn sync_vs_async.sync_fastapi:app --port 8001

# Async app (uses httpx)
uvicorn sync_vs_async.async_fastapi:app --port 8002
```

### 2. Load Test with Locust
```bash
locust -f sync_vs_async/load_test_locustfile.py
```

Open [http://localhost:8089](http://localhost:8089) to start testing.

### 3. Run Notebook
You can open the Jupyter notebook locally:
```bash
jupyter notebook notebooks/concurrency_demo.ipynb
```

Or use Google Colab:
```
https://colab.research.google.com/github/your-username/python-async-guide/blob/main/notebooks/concurrency_demo.ipynb
```

## 📂 Contents

- `sync_vs_async/`: FastAPI apps using sync and async I/O
- `examples/`: Threading, multiprocessing, and async demos
- `benchmarks/`: Output of load testing tools
- `notebooks/`: Interactive walkthroughs

## ✍️ License
MIT License
