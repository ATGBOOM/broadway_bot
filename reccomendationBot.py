import json
from typing import Dict, List, Any, Tuple
from dataService import ProductDataService 
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')
json_file = "fashion_ai_training_data.json"


class RecommendationService:
    def __init__(self):
        """Initialize the Recommendation Service."""
        self.product_service = ProductDataService(json_file)
        self.all_products = self._load_all_products()
        self.categories = list(self.all_products.keys())
        self.client = OpenAI()
    
    def _load_all_products(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load all products from the ProductDataService organized by category."""
        products_by_category = {}
        
        for category, subcategories in self.product_service.categories.items():
            if category not in products_by_category:
                products_by_category[category] = []
                
            for subcategory, products in subcategories.items():
                for product in products:
                    enhanced_product = product.copy()
                    enhanced_product['category'] = category
                    enhanced_product['subcategory'] = subcategory
                    brand_id = product.get('brand_id')
                    if brand_id and brand_id in self.product_service.brands:
                        enhanced_product['brand_name'] = self.product_service.brands[brand_id].get('brand_name', brand_id)
                    else:
                        enhanced_product['brand_name'] = brand_id or 'Unknown'
                    products_by_category[category].append(enhanced_product)
        
        return products_by_category

    def get_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all products from a specific category."""
        return self.all_products.get(category, [])

    def get_products_by_subcategory(self, subcategories):
        products_by_subcategory = {}
        print((self.product_service.categories.items()).get('Swimwear'))
        for category, subcategory in self.product_service.categories.items():
            #print(subcategory)
            if subcategory in subcategories:
                print("subcategory", subcategory)
                products_by_subcategory[subcategory] = subcategory.items()
                    
        return products_by_subcategory
    
    def get_all_products_flat(self) -> List[Dict[str, Any]]:
        """Get all products as a flat list."""
        all_products = []
        for products in self.all_products.values():
            all_products.extend(products)
        return all_products

    def get_complements(self, tags, sub_categories, user_query, aitext ):
        all_products = self.product_service.get_subcategory_data(sub_categories)
        return_prods = []
        
        for subcat in sub_categories:
            # if subcat.capitalize() not in all_products:
            #     continue
    
            complements = []
            if subcat not in all_products.keys():
                print(subcat, all_products.keys())
                continue
            prods = all_products[subcat]
            
            for prod in prods:
         
                if len(set(prod.get('tags')) & set(tags)) > 1:
           
                    complements.append({
                        'product_id': prod.get('product_id'),
                        'title': prod.get('title'),
                        'brand_name': prod.get('brand_name'),
                        'price': prod.get('price'),
                        #'average_rating': prod.get('average_rating'),
                        'tags': set(prod.get('tags')) & set(tags),
                    })
            complements.sort(key=lambda x: len(x['tags']), reverse=True)
        
            prod_ids = self.checkRecs(f"{aitext} {user_query}", "", complements[:20])
            filtered_complements = [comp for comp in complements if comp['product_id'] in prod_ids][:5]

            return_prods.extend(filtered_complements[:4])
        return return_prods

    def convert_to_searchable_tags(self, user_query, conversation_history, all_input_tags, allowed_categories) -> Tuple[List[str], List[str], str]:
        
        prompt = f"""
You are a fashion and beauty tagging engine for a personal shopping AI assistant.

You will receive a **set of tags** describing a user’s fashion or beauty needs. These tags should be interpreted **together as a single context** (not individually) to generate a cohesive recommendation profile. You will then generate **searchable tags** for relevant products, based only on the specified product categories.

---

**INPUT TAGS:**  
{all_input_tags}

**ALLOWED CATEGORIES (limit results to only these):**  
{allowed_categories}  
(e.g., ["Accessories", "Clothing"], or ["Makeup"], or ["Footwear", "Fragrance"])

---

**YOUR TASK:**

1. **Contextual Understanding:**  
   Interpret the full tag set collectively to understand the scenario (e.g., occasion, gender, mood, time of day, color theme, etc.). Do not treat tags individually — your job is to infer what would match *holistically* with the look, mood, and context.

2. **Generate Complementary Tags (Category-Constrained):**  
   - Create a practical and cohesive set of product tags for items that belong **only to the specified categories**.
   - Do not include items or tags from categories that are not listed in `ALLOWED CATEGORIES`.  
     *Example:* If only "Accessories" is allowed, do not suggest clothing, footwear, or makeup tags.

3. **Normalize All Tags**  
   - Use lowercase only  
   - Use hyphens for multi-word tags (e.g., “beard oil” → `beard-oil`)
   - Avoid repeating any of the input tags unless transformed or categorized
   - Generate single word tags rather than multiword

4. **Classify Tags into Two Groups**

   
   IMPORTANT:
   - Product types (e.g., watch, cufflinks, bracelet, belt, sunglasses, eyeshadow, lipstick, shampoo, loafers, heels, shirt, bag)
   - Gender (e.g., mens, womens, unisex)
   - Occasion-specific or use-case tags (e.g., gym, date-night, party, office-wear)
   - Formality levels (e.g., casual, formal, smart-casual, comfortable)
   - Generate 5-10 of these

   These are essential for filtering products and should always be included in this section if applicable.

   REGULAR:
   - Materials, finishes, or styles (e.g., cotton, silk, matte, polished, breathable)
   - Colors and tones (e.g., rose-gold, pink, jewel-tones, dark, blue, green)
   - Aesthetic tags and trends (e.g., elegant, classic, vintage, chic, minimal)
   - Texture/formula/skincare (e.g., creamy, glowy, water-resistant, oily-skin)
   - Budget/value-related (e.g., luxury, budget-friendly)
   - Generate 12-15 of these
---

KEY INSTRUCTIONS:
- Use the entire tag list as a unified profile
- Return tags only from the allowed categories
- Do not suggest unrelated product types or categories
- The goal is to generate powerful, searchable tags for recommendation systems


---

OUTPUT FORMAT (STRICT) DO NOT MAKE IT BOLD:

IMPORTANT:
- product-type1, product-type2, gender-tag, formality-tag, occasion-tag, etc.

REGULAR:
- supporting-style1, color1, aesthetic1, material1, etc.

RESPOND EXACTLY IN THE FORMAT ABOVE
"""


        try:
            response = self._call_ai(prompt)
            return self._parse_searchable_tags_response(response)
        except Exception as e:
            print(f"Error converting tags: {e}")
            return self._fallback_tags(all_input_tags)

    def _parse_searchable_tags_response(self, ai_response: str) -> Tuple[List[str], List[str], str]:
        """Parse AI response for searchable tags"""
        important_tags, regular_tags, category = [], [], "Clothing"
        current_section = None
        
        for line in ai_response.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('IMPORTANT:'):
                current_section = 'important'
                continue
            elif line.startswith('REGULAR:'):
                current_section = 'regular'
                continue
            elif line.startswith('- ') and current_section in ['important', 'regular']:
                # Parse line like "- CategoryName: tag1, tag2, tag3"
                category_part = line[2:]  # Remove '- '
                
                tags = [tag.strip() for tag in category_part.split(',') if tag.strip()]
                if current_section == 'important':
                    important_tags.extend(tags)
                elif current_section == 'regular':
                    regular_tags.extend(tags)
        
        # Remove duplicates while preserving order
        important_tags = list(dict.fromkeys(important_tags))[:8]
        regular_tags = list(dict.fromkeys(regular_tags))[:12]
        
        print(f"Parsed important tags: {important_tags}")
        print(f"Parsed regular tags: {regular_tags}")

        
        return important_tags, regular_tags

    def _fallback_tags(self, input_tags) -> Tuple[List[str], List[str], str]:
        """Generate fallback tags if AI fails"""
        tag_mapping = {
            'wedding': ['wedding', 'formal', 'ethnic-wear'],
            'work': ['office-wear', 'professional', 'business-casual'],
            'party': ['party-wear', 'festive', 'evening-wear'],
            'formal': ['formal', 'dressy', 'elegant'],
            'casual': ['casual', 'everyday', 'comfortable']
        }
        
        important_tags = []
        for tag in input_tags:
            if isinstance(tag, str) and tag.lower() in tag_mapping:
                important_tags.extend(tag_mapping[tag.lower()])
            else:
                important_tags.append(str(tag).lower().replace(' ', '-'))
        
        return list(set(important_tags))[:8], [], "Clothing"

    def checkRecs(self, user_query, conversation_history, products) -> List[str]:
        # Format products for the prompt in a cleaner way
        formatted_products = []
        for i, product in enumerate(products, 1):  # Limit to top 10 for better processing
            product_info = f"""
    {i}. PRODUCT_ID: {product.get('product_id', 'N/A')}
    TITLE: {product.get('title', 'N/A')}
    BRAND: {product.get('brand_name', 'N/A')}
    PRICE: ₹{product.get('price', 'N/A')}
"""
            formatted_products.append(product_info)
        
        products_text = '\n'.join(formatted_products)
        
        prompt = f"""
You are a fashion recommendation validator. Your job is to analyze if the recommended products truly match what the user is asking for.

**USER QUERY:** {user_query}
**CONVERSATION HISTORY:** {conversation_history}

**RECOMMENDED PRODUCTS:**
{products_text}

**YOUR TASK:**
1. **Analyze the user's request** - What specific product type, style, occasion, or characteristics are they looking for?
2. **Evaluate each product** - Does it match the user's core requirements?
3. **Select the best matches** - Return ONLY products that genuinely fit the user's request
4. **Prioritize relevance** - A pematch is better than a high-scoring irrelevant item

**EVALUATION CRITERIA:**
- **Product Type Match**: If user asks for "shirts", only recommend actual shirts/tops, not dresses or pants
- **Location Type Match**: If a specific location is mentioned, validate products that are appropriate for that location
- **Gender Match**: If user specifies "women's" or "men's", ensure gender appropriateness
- **Occasion Match**: If user mentions specific occasion (work, party, casual), prioritize those
- **Style Consistency**: Ensure the style aligns with user's aesthetic preferences

**CRITICAL RULES:**
- Return MAXIMUM 5 product IDs
- If NO products match well, return: "NO_MATCHES"
- If products match but not perfectly, still include them if they're reasonable alternatives

**OUTPUT FORMAT (VERY IMPORTANT):**
Return ONLY the product IDs in this exact format:
PROD001, PROD005, PROD012

If no good matches:
NO_MATCHES

**RESPONSE:**"""

        try:
            response = self._call_ai(prompt)
            
            
            # Clean and parse the response
            response = response.strip()
            
            # Handle no matches case
            if "NO_MATCHES" in response.upper() or "NO MATCHES" in response.upper():
                print("AI determined no good matches")
                return []
            
            # Extract product IDs using regex for more robust parsing
            import re
            product_ids = re.findall(r'PROD\d+', response.upper())
            
            # Remove duplicates while preserving order
            seen = set()
            unique_product_ids = []
            for prod_id in product_ids:
                if prod_id not in seen:
                    seen.add(prod_id)
                    unique_product_ids.append(prod_id)
            
            # Limit to maximum 5 as specified
            final_product_ids = unique_product_ids[:5]
            
            print(f"Validated Product IDs: {final_product_ids}")
            return final_product_ids
            
        except Exception as e:
            print(f"Error in checkRecs: {e}")
            # Fallback: return top 3 products if AI validation fails
            fallback_ids = [p.get('product_id') for p in products[:3] if p.get('product_id')]
            print(f"Fallback to top products: {fallback_ids}")
            return fallback_ids

    def get_categories_product_tags(self, user_input, context):
        
        subcategory_keys = list(self.product_service.get_subcategories_available().get("subcategories").keys())

        prompt = f""""
USER QUERY: {user_input}
CONTEXT: {context}
AVAILABLE SUBCATEGORIES: {subcategory_keys}

You are a fashion and beauty tagging assistant for Broadway.

Your task is to:
1. Analyze the user's query and context.
2. If the user is seeking product recommendations:
    - Identify and return a list of relevant subcategories from the provided list only
    - Generate 8–15 associated descriptive tags that reflect the user's intent, product style, use-case, fit, vibe, season, or preferences. These will help in matching the right products.

If the user is asking for general information (not product recommendations), return:
None

---

**Output Format:**
If the query is informational:
None

If the query is product-based:
{{
  "subcategories": ["Exact Subcategory 1", "Exact Subcategory 2"],
  "tags": ["tag1", "tag2", "tag3", ..., "tag15"]
}}

Make sure to:
- Only use subcategory names from the given list.
- Ensure the tags are descriptive, relevant, and varied (e.g., "minimalist", "stretch denim", "lightweight", "vacation-ready", "classic fit", "boho", "monochrome", etc.)
- Return only valid JSON without explanations or formatting.
"""

        

        response = self._call_ai(prompt).strip()
            
        # Find JSON content
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx != -1 and end_idx != 0:
            json_content = json.loads(response[start_idx:end_idx])
            print(json_content)
            return json_content['subcategories'], json_content['tags']
        else:
            raise ValueError("No JSON found in response")
            

    def _call_ai(self, prompt):
        """Send prompt to AI model."""
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                top_p=1,
                frequency_penalty=0,
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"AI API error: {e}")
            return ""
    
    def get_general_reccomendations(self, user_query, context):
        sub_categories, tags = self.get_categories_product_tags(user_query, context)
        all_products = self.product_service.get_subcategory_data(sub_categories)
        return_prods = []
        
        for subcat in sub_categories:
            complements = []
            if subcat not in all_products.keys():
                continue
            prods = all_products[subcat]
            
            for prod in prods:
                
                if len(set(prod.get('tags')) & set(tags)) > 1:
                    print(prod.get('title'))
                    complements.append({
                        'product_id': prod.get('product_id'),
                        'title': prod.get('title'),
                        'brand_name': prod.get('brand_name'),
                        'price': prod.get('price'),
                        #'average_rating': prod.get('average_rating'),
                        'tags': set(prod.get('tags')) & set(tags),
                    })
            complements.sort(key=lambda x: len(x['tags']), reverse=True)
        
            prod_ids = self.checkRecs(f"{user_query}", "", complements[:20])
            filtered_complements = [comp for comp in complements if comp['product_id'] in prod_ids][:5]

            return_prods.extend(filtered_complements[:4])
        return return_prods


    def get_recommendations(self, user_query: str, tags, gender = None, sub_categories=None, 
                          conversation_history: str = "", top_n: int = 5) -> List[Dict[str, Any]]:
        """Get product recommendations based on tags."""
        
        print("tags", tags)
        important_tags, regular_tags = self.convert_to_searchable_tags(user_query, conversation_history, tags, sub_categories)
        tags = important_tags + regular_tags
        all_products = self.product_service.get_subcategory_data(sub_categories)
        return_prods = []
        
        for subcat in sub_categories:
            # if subcat.capitalize() not in all_products:
            #     continue
    
            complements = []
            prods = all_products[subcat]
            
            for prod in prods:
         
                if len(set(prod.get('tags')) & set(tags)) > 1:
                    print(prod.get('title'))
                    complements.append({
                        'product_id': prod.get('product_id'),
                        'title': prod.get('title'),
                        'brand_name': prod.get('brand_name'),
                        'price': prod.get('price'),
                        #'average_rating': prod.get('average_rating'),
                        'tags': set(prod.get('tags')) & set(tags),
                    })
            complements.sort(key=lambda x: len(x['tags']), reverse=True)
            print(user_query)
            prod_ids = self.checkRecs(f"{user_query}", "", complements[:20])
            filtered_complements = [comp for comp in complements if comp['product_id'] in prod_ids][:5]

            return_prods.extend(filtered_complements[:4])
        return return_prods

