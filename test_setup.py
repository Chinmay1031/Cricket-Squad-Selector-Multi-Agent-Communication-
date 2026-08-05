import openai
import anthropic
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

print("OpenAI key loaded:", bool(os.getenv("OPENAI_API_KEY")))
print("Anthropic key loaded:", bool(os.getenv("ANTHROPIC_API_KEY")))
print("All packages imported successfully!")