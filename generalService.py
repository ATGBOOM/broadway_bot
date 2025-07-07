import json
from openai import OpenAI
from reccomendationBot import RecommendationService

class GeneralService:
    def __init__(self):
        self.client = OpenAI()
        self.reccomendation = RecommendationService()

    def respond(self, context, user_query):
        dialogue, rec = self.respond_text(context, user_query)
        if rec:
            prods = self.reccomendation.get_general_reccomendations(user_query, context)
            print ("there are the prods")
            if not prods:
                dialogue = self.noRecs(dialogue)
               
            return dialogue, prods
        return dialogue, None


    def noRecs(self, dialogue):
        prompt = f"""

            Remove followup questions and add an apology for not having reccomendations in the text below
            {dialogue}

    """
        return self._call_ai(prompt)

    def respond_text(self, context, user_query):
        prompt = f"""
You are an intelligent, humorous, and insightful shopping assistant for the brand **Broadway**, which offers a wide range of fashion, beauty, and personal care products.

---

USER QUERY:
{user_query}

CONTEXT:
{context}

---

Your goal is to:
1. **Classify the user's query** as either:
   - **Information-based** (asking for general knowledge, tips, or explanations)
   - **Product-based** (looking for recommendations, outfit ideas, pairings, or shopping help)

2. If the query is **information-based**, answer it directly and clearly in a helpful tone.

3. If the query is **product-based** or cannot be accurately resolved with just the given context, ask **smart follow-up questions** that nudge the user to provide more details and help activate one of our 3 core microservices. But do not ask follow-ups if the query already clearly indicates the use-case.

The 3 core microservices are:
- **Occasion** (e.g. dressing for a wedding, dinner, office, etc.)
- **Pairing** (e.g. what to wear with jeans, a red top, white sneakers)
- **Vacation** (e.g. packing suggestions for a location or climate)

STRICT RULES:
1) YOU ARE NOT TO SPEAK ABOUT BRANDS NOT IN THE BROADWAY CATALOGUE
2) DO NOT SPEAK NEGATIVELY ABOUT BROADWAY OR ANY SPECIFIC BRAND
3) DO NOT LIST RECCOMENDATIONS IN THE RESPONSE
4) YOU ARE ALWAYS TO RETURN A RESPONSE

---

**OUTPUT FORMAT:**
Return ONLY a valid JSON object like this:
{{
  "dialogue": "Your friendly and helpful response goes here, including any questions if needed.",
  "recommendation": true or false  // true if user wants or is nudged toward product recommendations, false if only information was requested
}}

Examples:
- For "What’s the use of toner?":
{{
  "dialogue": "Toner helps cleanse and prep your skin by removing any leftover residue after washing, and it can balance your skin's pH before moisturizing.",
  "recommendation": false
}}

- For "Show me outfit ideas for a beach vacation":
{{
  "dialogue": "Got it! For a beach vacation, would you prefer relaxed daytime outfits, or something chic for evenings by the water?",
  "recommendation": true
}}

Do not return anything outside of the JSON object. Be warm, clear, and concise.
"""


        response = self._call_ai(prompt).strip()
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx != -1 and end_idx != 0:
            json_content = json.loads(response[start_idx:end_idx])
            return json_content['dialogue'], json_content['recommendation']
        else:
            raise ValueError("No JSON found in response")

    def _call_ai(self, prompt: str) -> str:
        """Send prompt to AI and get response."""
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return completion.choices[0].message.content
    