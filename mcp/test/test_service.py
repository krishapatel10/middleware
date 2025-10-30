# mcp/test/test_service.py
import asyncio
import json
import os
import sys

# ensure project root is on path when running the file directly
if __name__ == "__main__" and __package__ is None:
    # allow running like: python mcp/test/test_service.py
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from mcp.services.llm_service import LLMService
from mcp.schemas import ReviewLLMOutput  # or from mcp.schemas depending on where you put it

# mcp/test/test_service.py
# (only the main() function area shown — replace your current main with this)

async def main():
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    print("GEMINI_API_KEY set:", bool(key))

    service = LLMService()
    try:
        sample_review = (
            "The report is clear and well-structured, but lacks any quantitative evaluation. "
            "Methodology is reasonable but missing baseline comparisons. The writing is generally professional."
        )

        print(" Calling evaluate_and_parse (this will use temperature=0 and retries)...")
        validated = await service.evaluate_multiple_times(sample_review, temperature=0.0)

        out = validated.dict(by_alias=True)
        print("\n Validated ReviewLLMOutput (pretty):")
        print(json.dumps(out, indent=2, ensure_ascii=False))

        with open("tmp_service_result.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print("\nSaved validated output to tmp_service_result.json")

    except Exception as e:
        # Make sure we print a helpful debugging message
        print("\n Service test failed:", repr(e))
        # If the service captured last raw output inside the ValueError message, print it.
        # This helps debugging without re-running with debug logs.
        try:
            # the ValueError includes the last_raw in its message in our implementation
            print("\nFull exception details:", e)
        except Exception:
            pass
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())
