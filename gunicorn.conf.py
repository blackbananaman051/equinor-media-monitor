workers = 1
timeout = 120

def on_starting(server):
    from scheduler import start_scheduler
    start_scheduler()
