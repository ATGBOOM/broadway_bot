import json
from openai import OpenAI

from dataService import ProductDataService
from reccomendationBot import RecommendationService
import os

class PairingService:

    def __init__(self):
        self.client = OpenAI()
        self.reccomendations = RecommendationService()
        self.data_service = ProductDataService()
        self.sub_categories = self.data_service.get_subcategories_available()
    # def getComplementProductTags(self, user_query):
    #     prompt = f"""
    # **Your Role:** You are an expert fashion stylist AI. Your goal is to generate a list of tags to find complementary fashion items that match the style and context described by the user.

    # ---

    # **INPUT FORMAT:**
    # You will receive a user query describing one or more clothing items (e.g., "floral shirt", "black jeans") and may also include an occasion or context (e.g., "for a brunch", "for a party").

    # ---

    # **YOUR TASK:**
    # 1. Analyze the core style, material, color, and occasion based on the query.
    # 2. Generate a **single, comma-separated list of 15–20 tags** that describe **complementary fashion items**.
    # 3. Follow this rule for composition:
    # - Include **2–3 product types** (e.g., `shoes`, `bag`, `jacket`, `t-shirt`) — these should not include the base item itself.
    # - The remaining tags must be **descriptive styling attributes** that match the vibe, such as color, texture, mood, and context (e.g., `vintage`, `linen`, `coastal`, `breezy`, `tailored`, `bold print`, `minimalist`).

    # ---

    # **EXAMPLES:**

    # **Query:** "What should I wear with a floral shirt for a brunch?"  
    # **Output:** chinos, espadrilles, tote bag, casual, light cotton, soft tones, relaxed, spring, breathable, tailored, beige, sunny, open collar, neutral, laid-back, woven

    # **Query:** "Complementary items for black jeans for a concert"  
    # **Output:** boots, leather jacket, t-shirt, edgy, black, street style, distressed, rocker, casual, concert-ready, modern, graphic print, dark tones, silver, bold, minimal

    # **Query:** "What goes well with pastel shorts for a picnic?"  
    # **Output:** polo shirt, canvas sneakers, tote bag, pastel, relaxed, cotton, breathable, light tones, cheerful, outdoorsy, spring-ready, picnic vibe, subtle, sunny

    # ---

    # **User Query:** {user_query}

    # **Output:**
    # """

    #     response = self.ask_ai(prompt)
    #     parsed_tags = response.split(', ')
    #     return parsed_tags

    def getComplementProductTags(self, user_query, bot_response):
        subcategories = self.sub_categories.get("subcategories").keys()
   
        prompt = f"""
**Your Role:** You are an expert fashion stylist AI. Your job is to generate smart, searchable styling tags **and recommend subcategories** from which to fetch products that go well with the fashion item(s) described by the user.

---

**INPUT FORMAT:**  
You will receive a natural language query from the user that includes:
- One or more fashion items (e.g., "floral shirt", "black jeans")  
- Optional context or occasion (e.g., "for a brunch", "for a wedding", "for walking in the city")

USER QUERY : {user_query}
CONTEXT : {bot_response}
SUB CATEGORIES AVAILABLE : {subcategories}

---

**YOUR TASK:**  
1. Analyze the full query to identify:
   - The **base item(s)** (what the user is wearing or referencing)
   - The **goal** (do they want full outfit suggestions or specific item types like just shoes or jackets?)
   - Any **occasion**, **season**, or **style cues**

2. Generate a list of **15–20 complementary product tags**:
   - Include **2–3 product types** that match the goal (e.g., `jacket`, `loafers`, `backpack`)  
     - ⚠️ These must **not repeat** the user’s original product  
     - ⚠️ These must come from the **appropriate category** based on the query
   - The rest should include:
     - **Color tags** that pair well with the core item (4–6)
     - **Material or texture** (e.g., cotton, leather, linen, denim, ribbed)
     - **Style/mood descriptors** (e.g., casual, edgy, breezy, modern, chic)

3. Choose 2–5 **subcategories** that should be queried to fetch real products for the user.
     - Base this on the **intent of the user’s request**.
     - If the user asks *"what goes with black jeans"* → include jackets, shoes, tops, accessories, etc.
     - If the user says *"what shoes go with black jeans"* → restrict to only footwear-related subcategories
     - Use only real subcategories provided

---

**RESPONSE FORMAT (STRICT JSON ONLY):**
```json
{{
  "tags": [
    "tag1", "tag2", "tag3", ...
  ],
  "subcategories": [
    "subcategory1", "subcategory2", ...
  ]
}}
"""

        response = self.ask_ai(prompt)
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        json_content = response[start_idx:end_idx]
     
        parameters = json.loads(json_content)
        print(parameters['tags'], parameters['subcategories'])
        return parameters['tags'], parameters['subcategories']


    def getComplementProducts(self, user_query, bot_input):
        """
        Retrieves complementary products based on the provided product and tags.
        """
      
        tags, subcategories = self.getComplementProductTags(user_query, bot_input)
        print("tags are:", tags)
        
        return self.reccomendations.get_complements( tags, subcategories, user_query, "what will go well with")


    def ask_ai(self, prompt):
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return completion.choices[0].message.content


if __name__ == "__main__":
    service = PairingService()

    
    prods = service.getComplementProducts('what shoes would go well with my denim jacket')
 

    for comp in prods:
        print(f"  - {comp['title']} (ID: {comp['product_id']}) - {comp['brand_name']} - ${comp['price']} - {comp['tags']}")
    
