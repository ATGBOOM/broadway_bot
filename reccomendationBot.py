from typing import Dict, List, Optional, Any, Tuple
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
    
    def get_all_products_flat(self) -> List[Dict[str, Any]]:
        """Get all products as a flat list."""
        all_products = []
        for products in self.all_products.values():
            all_products.extend(products)
        return all_products

    def convert_to_searchable_tags(self, user_query, conversation_history, all_input_tags) -> Tuple[List[str], List[str], str]:
        """Convert input tags to searchable product catalog tags."""
        if not all_input_tags:
            return [], [], "Clothing"
        
        prompt = f"""
You are a product tagging engine for an AI fashion assistant.

You will be given structured user parameters extracted from a conversation. Your job is to generate **searchable product tags** from these parameters to help match products from our fashion catalog.

---

**PARAMETERS:**
{all_input_tags}

---

**YOUR TASK:**

1. Convert the parameter values into realistic, normalized e-commerce tags:
   - All lowercase
   - Use hyphens for multi-word tags (e.g., "office wear" → "office-wear")

2. **Infer appropriate product types** based on occasion, gender, weather, formality, time of day, and age.
   - Example: For a party at night for men, suggest items like "shirt", "trousers", "loafers"
   - Example: For a beach vacation in hot weather, suggest items like "shorts", "t-shirts", "sandals"

3. Classify tags into two groups:
   - **IMPORTANT**:
     - Product types (e.g., t-shirt, dress, jeans, loafers)
     - Gender (e.g., mens, womens, unisex)
     - Occasion or context-specific tags (e.g., gym-wear, office-wear, wedding-guest)
     - Formality level (e.g., casual, formal, smart-casual)

   - **REGULAR**:
     - Fabrics, styles, comfort (e.g., cotton, flowy, wrinkle-free)
     - Colors and tones (e.g., beige, jewel-tones, neutral)
     - Moods, aesthetics, trends (e.g., edgy, vintage, chic, y2k)
     - Weather-related attributes (e.g., warm, breathable, rain-friendly)
     - Body-fit attributes (e.g., petite, plus-size, tall)
     - Budget implications (e.g., premium, budget-friendly)

4. Group the tags under logical high-level categories such as:
   - Clothing
   - Footwear
   - Accessories
   - Fabric
   - Color
   - Style
   - Fit
   - Occasion

---

**OUTPUT FORMAT (STRICT):**

IMPORTANT:
- CategoryName: tag1, tag2
- CategoryName: tag1

REGULAR:
- CategoryName: tag1, tag2, tag3
- CategoryName: tag1, tag2

---

Now, using the parameters, generate the most accurate and practical tags possible to guide product search. Remember to include inferred product types based on the full context.
"""


        try:
            response = self._call_ai(prompt)
            print(f"Tag conversion response: {response}")
            return self._parse_searchable_tags_response(response)
        except Exception as e:
            print(f"Error converting tags: {e}")
            return self._fallback_tags(all_input_tags)

    def _parse_searchable_tags_response(self, ai_response: str) -> Tuple[List[str], List[str], str]:
        """Parse AI response for searchable tags"""
        important_tags, regular_tags, category = [], [], "Clothing"
        current_section = None
        
        print(f"Parsing AI response: {ai_response}")
        
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
                
                if ':' in category_part:
                    # Split by first colon to get category and tags
                    category_name, tags_str = category_part.split(':', 1)
                    category_name = category_name.strip()
                    
                    # Set the main category (use the first one we see)
                    if category == "Clothing" and category_name in self.categories:
                        category = category_name
                    
                    # Extract tags
                    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                    
                    if current_section == 'important':
                        important_tags.extend(tags)
                    elif current_section == 'regular':
                        regular_tags.extend(tags)
                else:
                    # Handle lines that might just be tags without category
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

        
        return important_tags, regular_tags, None
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
    MATCHED_IMPORTANT_TAGS: {', '.join(product.get('matched_important_tags', []))}
    MATCHED_REGULAR_TAGS: {', '.join(product.get('matched_regular_tags', []))}
    TOTAL_SCORE: {product.get('total_score', 0)}"""
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

    def _call_ai(self, prompt):
        """Send prompt to AI model."""
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"AI API error: {e}")
            return ""

    def get_recommendations(self, user_query: str, tags, gender = None, category_name=None, 
                          conversation_history: str = "", top_n: int = 7) -> List[Dict[str, Any]]:
        """Get product recommendations based on tags."""
        
        important_tags, regular_tags, category_name = self.convert_to_searchable_tags(user_query, conversation_history, tags)
        
        print(important_tags, regular_tags, category_name)
        # Get candidate products
        if category_name and category_name in self.categories:
            candidate_products = self.get_products_by_category(category_name)
        else:
            candidate_products = self.get_all_products_flat()
        
        # Score and match products
        product_matches = []
        print("gender is " + gender[0])
        for product in candidate_products:
            product_tags = product.get('tags', [])
            
            important_matches = sum(1 for tag in important_tags if tag in product_tags)
            regular_matches = sum(1 for tag in regular_tags if tag in product_tags)
            total_score = (important_matches * 5) + regular_matches
            if gender and gender[0] not in product_tags:
                continue
            if important_matches > 0 and regular_matches >= 1:
                print(product.get('title'))
                matched_important = [tag for tag in important_tags if tag in product_tags]
                matched_regular = [tag for tag in regular_tags if tag in product_tags]
                
                product_matches.append({
                    'product_id': product.get('product_id'),
                    'title': product.get('title'),
                    'brand_name': product.get('brand_name'),
                    'price': product.get('price'),
                    'average_rating': product.get('average_rating'),
                    'total_score': total_score,
                    'matched_important_tags': matched_important,
                    'matched_regular_tags': matched_regular,
                    'important_matches': important_matches,
                    'regular_matches': regular_matches,
                    'banned_matches': 0,
                    'matched_banned_tags': [],
                    'weighted_score': total_score
                })
        
        # Sort by score and validate
        product_matches.sort(key=lambda x: (x['total_score'], x.get('average_rating', 0)), reverse=True)
        print("product matches found: " + str(len(product_matches)))
        if product_matches:
            validated_ids = self.checkRecs(user_query, conversation_history, product_matches[:20])
            final_matches = [p for p in product_matches if p['product_id'] in validated_ids]
            return final_matches[:top_n]
        
        return []