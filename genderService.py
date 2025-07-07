from openai import OpenAI

class GenderService:
    
    def __init__(self) -> None:
        self.client = OpenAI()
        pass

    def getGender(self, context, query, gender = None):
        
        prompt = f"""
You are a smart AI assistant that classifies gender intent for fashion and beauty product recommendations.

You are given:
- CONTEXT: The conversation history or previous user inputs
- USER INPUT: The user’s most recent message
- PREVIOUSLY KNOWN GENDER: Gender inferred from earlier conversation, if available

---

CONTEXT:
{context}

USER INPUT:
{query}

PREVIOUSLY KNOWN GENDER:
{gender}

---

### Your task:

1. First, determine if the user query is:
   - A **general or informational query** (e.g. "What’s trending at the Met Gala?", "How to apply sunscreen", "Tell me a joke")  
   - A **specific product-related or personal recommendation request** (e.g. "Show me red dresses", "What should I wear to a wedding?")

2. If the query is **not about a personal or specific product recommendation**, or is about fashion/beauty in general:
   → return **"Not_Needed"**

3. If the query:
   - Clearly implies a **gender** (e.g., "for my boyfriend", "as a girl", "boxers") → return **"Male"** or **"Female"**
   - Is **unisex in nature** (e.g. “moisturizer”, “white sneakers”, “oversized hoodie”) → return **"Unisex"**
   - Is **too vague or ambiguous** for gender-based product targeting and requires reccomendations → return **"None"**

4. If a **previously known gender** exists and the current query **still applies to that person**, return that gender — unless the query is about someone else.
5. If previous gender is not need but current user input needs a gender related query - provide a gender.
---

### Return only one of the following (case-sensitive):
Male  
Female  
Unisex  
Not_Needed
None
"""

        return self._call_ai(prompt).strip()


    def _call_ai(self, prompt: str) -> str:
        """Send prompt to AI and get response."""
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.1,
            messages=[
                {"role": "user", "content": prompt}
            ],
        
        )
        return completion.choices[0].message.content

