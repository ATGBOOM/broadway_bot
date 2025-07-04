import json
from typing import Dict, List, Optional, Any
from openai import OpenAI
import os
from dataService import ProductDataService
from reccomendationBot import RecommendationService

class VacationService:
    
    def __init__(self):
        """Initialize the VacationService with OpenAI client."""
        self.client = OpenAI()
        self.data_service = ProductDataService()
        self.sub_categories = self.data_service.get_subcategories_available()
        self.reccomendations = RecommendationService()
        # Popular destinations by region/state
        self.destination_map = {
            "goa": ["Baga Beach", "Old Goa Churches", "Dudhsagar Falls"],
            "kerala": ["Munnar Hill Station", "Alleppey Backwaters", "Fort Kochi"],
            "rajasthan": ["Jaipur City Palace", "Udaipur Lake Palace", "Jaisalmer Desert"],
            "himachal": ["Manali Adventure Sports", "Shimla Mall Road", "Kasol Valleys"],
            "kashmir": ["Dal Lake Srinagar", "Gulmarg Skiing", "Pahalgam Meadows"],
            "uttarakhand": ["Rishikesh Rafting", "Nainital Lakes", "Mussoorie Hills"],
            "maharashtra": ["Mumbai Marine Drive", "Lonavala Caves", "Aurangabad Ajanta"],
            "karnataka": ["Coorg Coffee Plantations", "Hampi Ruins", "Mysore Palace"],
            "tamil_nadu": ["Ooty Hill Station", "Mahabalipuram Temples", "Kodaikanal Lakes"],
            "west_bengal": ["Darjeeling Tea Gardens", "Kolkata Victoria Memorial", "Sundarbans"],
            "andhra_pradesh": ["Araku Valley", "Tirupati Temple", "Visakhapatnam Beaches"],
            "odisha": ["Puri Jagannath Temple", "Konark Sun Temple", "Chilika Lake"],
            "assam": ["Kaziranga National Park", "Majuli Island", "Kamakhya Temple"],
            "meghalaya": ["Shillong Living Root Bridges", "Cherrapunji Waterfalls", "Mawlynnong Village"],
            
            # International destinations
            "thailand": ["Bangkok Temples", "Phuket Beaches", "Chiang Mai Mountains"],
            "bali": ["Ubud Rice Terraces", "Seminyak Beaches", "Mount Batur Volcano"],
            "singapore": ["Gardens by Bay", "Marina Bay Sands", "Sentosa Island"],
            "dubai": ["Burj Khalifa", "Dubai Mall", "Desert Safari"],
            "maldives": ["Water Villas", "Coral Reefs", "Beach Resorts"],
            "nepal": ["Kathmandu Durbar Square", "Pokhara Lakes", "Everest Base Camp"],
            "bhutan": ["Paro Tiger's Nest", "Thimphu Dzongs", "Punakha Valley"],
            "sri_lanka": ["Kandy Temple", "Ella Tea Country", "Galle Fort"]
        }

    def get_vacation_recommendation(self, user_query, bot_input) -> Dict[str, Any]:
        """Main entry point - gets popular locations and outfit recommendations for a destination."""
        print("vacation debugging", user_query, bot_input)
        # Step 1: Extract destination from user query
        destination = self._extract_destination(user_query)
        
        if not destination:
            return {
                "error": "Could not identify destination from your query",
                "suggestion": "Please mention a specific place like 'Goa', 'Kerala', 'Thailand', etc."
            }
        
        # Step 2: Get popular locations for that destination
        popular_locations = self._get_popular_locations(destination, user_query, bot_input)
       
     
        dialogue = popular_locations.get('dialogue')
        print(dialogue)
        tag = self.reccomendations.convert_to_searchable_tags(
            user_query=user_query, 
            conversation_history=bot_input, 
            all_input_tags= popular_locations.get('outfit').get('style_palette'), 
            allowed_categories= popular_locations.get('outfit').get('categories')
            )
        tags = tag[1] + tag[0]
        print(popular_locations.get('outfit').get('categories'))
        print(tags)
        recs = self.reccomendations.get_complements(tags, popular_locations.get('outfit').get('categories'), dialogue, "")


            
        return dialogue, recs


    def _extract_destination(self, user_query: str) -> Optional[str]:
        """Extract destination from user query using AI."""
        
        
        prompt = f"""
Extract the main destination from this travel query. Return the destination name in lowercase, standardized format.

USER QUERY: {user_query}

Return the destination as:

Examples:
- "Planning a trip to Goa" → goa
- "Want to visit Kerala backwaters" → kerala  
- "Going to Thailand next month" → thailand
- "Paris vacation" → paris
- "Backpacking through Europe, starting in Italy" → italy
- "New York city break" → new_york
- "Japan cherry blossom tour" → japan
- "Bali honeymoon" → bali
- "London weekend getaway" → london
- "Rajasthan heritage tour" → rajasthan

If multiple destinations are mentioned, return the primary/main one.
If no clear destination is found, return "unknown".

DESTINATION:
"""
        
        try:
            response = self._call_ai(prompt).strip().lower()
            
            # Validate the response is a known destination
        
            return response
            
            # Fallback: keyword matching
            #return self._keyword_destination_fallback(user_query)
            
        except Exception as e:
            print(f"Error in destination extraction: {e}")
            return self._keyword_destination_fallback(user_query)

    def _keyword_destination_fallback(self, user_query: str) -> Optional[str]:
        """Simple keyword-based destination extraction as fallback."""
        user_lower = user_query.lower()
        
        # Check for exact matches first
        for destination in self.destination_map.keys():
            if destination in user_lower:
                return destination
        
        # Check for common alternate names
        alternate_names = {
            "bombay": "maharashtra",
            "mumbai": "maharashtra", 
            "delhi": "delhi",
            "bangalore": "karnataka",
            "chennai": "tamil_nadu",
            "kolkata": "west_bengal",
            "hyderabad": "andhra_pradesh",
            "pune": "maharashtra",
            "jaipur": "rajasthan",
            "udaipur": "rajasthan",
            "manali": "himachal",
            "shimla": "himachal",
            "darjeeling": "west_bengal",
            "ooty": "tamil_nadu",
            "munnar": "kerala",
            "rishikesh": "uttarakhand"
        }
        
        for city, state in alternate_names.items():
            if city in user_lower:
                return state
                
        return None

    def _get_popular_locations(self, destination: str, user_query, bot_input) -> List[str]:
        """Get 2-3 popular locations for the destination."""
        subcategory_keys = self.sub_categories.get("subcategories").keys()


        subcategories_str = ", ".join(subcategory_keys)
        
        prompt = f"""
You are a highly creative and knowledgeable AI fashion and travel stylist. Your expertise lies in blending practical travel needs with modern fashion aesthetics. For the given destination, you will generate a detailed and engaging travel and style guide.

DESTINATION: {destination}  
USER QUERY: {user_query}  
CONTEXT: {bot_input}  
SUBCATEGORIES: {subcategories_str}

Instructions:
1. If the user mentions a specific product or product type, focus the outfit recommendations and category selection only on that product and its relevant subcategories.
2. Analyze the destination’s culture, climate, and typical activities.
3. Generate a natural, friendly dialogue that blends fashion advice with a mini travel narrative.
4. Output your response strictly in the JSON format below — no markdown or explanation text.

---

RESPONSE FORMAT:
{{
  "dialogue": "Write a warm, conversational paragraph (not a list). Briefly describe the destination’s vibe and weather. Mention 2–3 common activities the user might do there. Recommend outfit ideas suited for those activities and the weather, using the requested product focus if any. Include a short explanation (1–2 sentences) of why these outfits work for the place. End with a follow-up question like: ‘Would you like a specific outfit idea for hiking or evening dinners?’",
  
  "outfit": {{
    "categories": ["Exact subcategories from the SUBCATEGORIES list only"],
    "style_palette": [
      "vibe_or_aesthetic_1",
      "vibe_or_aesthetic_2",
      "fabric_or_texture_1",
      "fabric_or_texture_2",
      "color_scheme_1",
      "color_scheme_2",
      "key_accessory_1",
      "key_accessory_2",
      "footwear_style",
      "...additional tags up to 15 total"
    ]
  }}
}}

---

Guidelines:

1.  **Popular Locations:**  The description for each location /activity should be brief and engaging.
2.  **Categories:** For each location, select 5-7 of the most relevant categories from the provided `SUBCATEGORIES` list. Use the exact wording and capitalization. If a specific product type is given by the user, choose subcategories of that product only.
3.  **Style Palette (The Core of the Prompt):** This is your creative signature. Instead of generic tags, create a "style palette" of 10-15 descriptive keywords.
    * **Vibe/Aesthetic:** Think in terms of style cores (e.g., 'bohemian chic', 'urban explorer', 'classic elegance', 'minimalist', 'gorpcore').
    * **Fabric/Texture:** Suggest materials that are both stylish and practical for the climate (e.g., 'lightweight linen', 'breathable cotton', 'wrinkle-resistant jersey', 'chunky knit').
    * **Color Scheme:** Recommend a color palette (e.g., 'earthy tones', 'neutral palette', 'vibrant tropicals', 'monochromatic').
    * **Key Accessories & Footwear:** Mention essential items that complete the look (e.g., 'crossbody bag', 'statement sunglasses', 'comfortable sneakers', 'strappy sandals').
4.  **Cultural Sensitivity:** Ensure outfit suggestions are respectful of local customs and dress codes, especially for religious or culturally significant sites.
5.  **Output Format:** You MUST return ONLY the raw JSON object. Do not include any introductory text, explanations, or markdown formatting like `json` before the opening `{{`.

"""

        try:
            response = self._call_ai(prompt)
            # Clean the response to extract JSON
            response = response.strip()
            
            # Find JSON content
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_content = response[start_idx:end_idx]
                return json.loads(json_content)
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            print(f"Error getting destination info: {e}")
            return self._get_fallback_destination_info(destination)


    def generate_dialogue(self, destination: str, weather, reccomendations):
    
        
        prompt =f"""
I will give you:
- The name of a location  - {destination}
- Current or forecasted weather at that location  - {weather}
- A list of outfit, activity, or product recommendations  {reccomendations}

Your task is to generate a friendly and engaging paragraph of dialogue that:
1. Gives a short, vivid context about the location — what it’s like or known for  
2. Explains why these recommendations are great for this location and weather  
3. Keep the dialogue less than 3 lines
Keep the tone warm, conversational, and useful — like a knowledgeable friend giving helpful advice.

"""


        try:
            return self._call_ai(prompt).strip()
     
        
        except Exception as e:
            print(f"Error generating outfit tags: {e}")
            return self._get_default_outfit_tags(destination)

    def _get_default_outfit_tags(self, destination: str) -> List[str]:
        """Fallback outfit tags based on destination type."""
        
        beach_destinations = ["goa", "maldives", "thailand", "bali"]
        mountain_destinations = ["himachal", "kashmir", "uttarakhand", "nepal", "bhutan"]
        cultural_destinations = ["rajasthan", "kerala", "tamil_nadu", "odisha"]
        
        if destination in beach_destinations:
            return ["sundresses", "swimwear", "beach cover-ups", "sandals", "sun hats", "light shirts", "shorts", "sunglasses"]
        elif destination in mountain_destinations:
            return ["warm jackets", "trekking shoes", "layered clothing", "sweaters", "jeans", "beanies", "gloves", "thermal wear"]
        elif destination in cultural_destinations:
            return ["modest clothing", "walking shoes", "light scarves", "cotton fabrics", "long pants", "covered tops", "comfortable flats"]
        else:
            return ["comfortable clothing", "walking shoes", "light jackets", "casual wear", "sun protection", "breathable fabrics"]

    def _create_summary(self, destination: str, popular_locations: List[str], outfit_tags: List[str]) -> str:
        """Create a friendly summary of the recommendations."""
        
        locations_text = ", ".join(popular_locations)
        outfit_text = ", ".join(outfit_tags[:6])  # Show first 6 tags
        
        return f"Perfect! For your {destination.title()} trip, I recommend visiting {locations_text}. For outfits, pack {outfit_text} and similar pieces to stay comfortable and stylish throughout your journey!"

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


def main():
    """Test function for VacationService."""
    print("🌍 Testing VacationService...")
    print("=" * 50)
    
    vacation_service = VacationService()
    
    # Test queries
    test_queries = [
        "Planning a trip to Paris"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🧪 Test {i}: '{query}'")
        print("-" * 40)
        
     
        recommendations = vacation_service.get_vacation_recommendation(query, "")
     
        
        


if __name__ == "__main__":
    main()