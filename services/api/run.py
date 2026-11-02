import argparse
import asyncio
import selectors
import sys
from pathlib import Path

import uvicorn


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


def main() -> None:
    parser = argparse.ArgumentParser(description="Lancer l'API Prisme")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    api_directory = Path(__file__).resolve().parent
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(api_directory),
        loop="run:selector_loop_factory" if sys.platform == "win32" else "auto",
    )


if __name__ == "__main__":
    main()
