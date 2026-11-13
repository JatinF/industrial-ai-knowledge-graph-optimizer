"""Console entry. demo runs the in-process failure flow. serve starts the API."""

import sys

from industrial_ai.demo import run_demo


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "demo"
    if command == "demo":
        print(run_demo(), end="")
        return
    if command == "serve":
        import uvicorn

        uvicorn.run("industrial_ai.api.main:app", host="127.0.0.1", port=8000)
        return
    raise SystemExit("usage: industrial-ai [demo|serve]")


if __name__ == "__main__":
    main()
