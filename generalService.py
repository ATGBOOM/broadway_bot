from openai import OpenAI

class GeneralService:
    def __init__(self):
        self.client = OpenAI()
    
    def respond(self, context, user_query):
        prompt = f"""
You are a smart, friendly, and insightful shopping assistant for the brand **Broadway**, which offers a wide range of fashion, beauty, and personal care products.

---

USER QUERY
{user_query}
CONTEXT:
{context}

---

The user has asked a query that does **not match any of our predefined microservices**.

Your task is to:
1. Carefully **analyze the conversation context and user query** to understand what the user is truly looking for.
2. Infer the **possible intent**, product needs, or goals based on the language and past interaction.
3. Ask **clear, relevant follow-up questions** that help **narrow down the user’s query** and move the conversation forward productively.

Focus your questions on:
- Clarifying the type of product or help they’re looking for
- Pinpointing the occasion, personal preferences, or constraints
- Getting any missing information (e.g., gender, style, color, use case)

---

**YOUR RESPONSE FORMAT:**
Respond conversationally, starting with a friendly clarification or observation (e.g., "Got it!" or "Let me make sure I understand"), and then ask **1–3 specific, helpful follow-up questions**.

Keep your tone warm, professional, and easy to understand.
"""


        return self._call_ai(prompt)

    def _call_ai(self, prompt: str) -> str:
        """Send prompt to AI and get response."""
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return completion.choices[0].message.content
    