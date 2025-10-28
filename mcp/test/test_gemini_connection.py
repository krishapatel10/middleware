# test_gemini_connection.py
import asyncio
from mcp.services.llm_client import LLMClient
from mcp.services.prompt import build_review_prompt

async def main():
    client = LLMClient()
    try:
        review_text = "This report is clear but lacks depth in the analysis section."
        prompt = build_review_prompt(review_text)

        print("Sending test prompt to Gemini...")
        response = await client.call_gemini(prompt, temperature=0.0)
        print("\n Gemini API Response:")
        print(response[:1000])  # print only first 1000 chars for readability

    except Exception as e:
        print(" Gemini connection test failed:", e)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
