bind = "0.0.0.0:8000"

workers = 4

worker_class = "uvicorn.workers.UvicornWorker"

timeout = 60

keepalive = 5