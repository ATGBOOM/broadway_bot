import os

# Set OpenAI API key as environment variable for Railway
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or "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"

# Set as environment variable so OpenAI can find it
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

print(f"✅ OpenAI API Key configured (length: {len(OPENAI_API_KEY)})")