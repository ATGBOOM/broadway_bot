from openai import OpenAI

class GenderService:
    
    def __init__(self) -> None:
        self.client = OpenAI()
        pass

    def getGender(self, context, query):
        
        prompt = f"""
You are a fashion assistant helping determine the intended gender for product recommendations.

You are given:
- CONTEXT: Previous conversation or interaction history  
- USER INPUT: The most recent query from the user  

---

CONTEXT:
{context}

USER INPUT:
{query}

---

Your task is to analyze the full context and determine the most appropriate gender for product recommendations.

Rules:
- If the gender is clearly implied or mentioned → return Male or Female
- If the product or query is clearly unisex or not gender-specific → return Unisex
- If gender cannot be confidently determined from the information → return None

---

Return only the gender as a single word (case-sensitive):
Male  
Female  
Unisex  
None
"""
        return self._call_ai(prompt).strip()


    def _call_ai(self, prompt: str) -> str:
        """Send prompt to AI and get response."""
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ],
        
        )
        return completion.choices[0].message.content

