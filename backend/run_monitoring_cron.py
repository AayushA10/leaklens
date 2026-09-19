import asyncio
import json

from services.monitoring_service import run_due_monitoring_scans


async def main():
    result = await run_due_monitoring_scans()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
