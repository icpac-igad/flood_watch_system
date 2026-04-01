"""Download orchestrator - delegates to the scheduler for all sync jobs"""
from .scheduler import start_scheduler


def main():
    """Entry point - starts the APScheduler-based job runner"""
    start_scheduler()


if __name__ == "__main__":
    main()
