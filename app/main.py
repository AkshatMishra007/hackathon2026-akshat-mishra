import asyncio

from app.config import get_settings
from execution.worker import run_support_workers


async def main() -> None:
    settings = get_settings()
    print("🚀 Starting workers...")
    
    results = await run_support_workers(settings)
    
    print("✅ Workers finished")
    print(f"Processed {len(results)} tickets. Logs saved to {settings.logs_dir}")

if __name__ == "__main__":
    asyncio.run(main())
