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

    def convert_to_searchable_tags(self, all_input_tags) -> Tuple[List[str], List[str], str]:
        """Convert input tags to searchable product catalog tags."""
        if not all_input_tags:
            return [], [], "Clothing"
        
        prompt = f"""Convert these tags into e-commerce product tags and categorize them.

INPUT TAGS: {all_input_tags}
CATEGORIES: {self.categories}

Convert tags to realistic product tags (lowercase, hyphens). Separate into:
- IMPORTANT: Direct requirements (product types, occasions, formality)
- REGULAR: Supporting tags (colors, aesthetics, comfort)

Format:
CATEGORY:
- CategoryName

IMPORTANT:
tag1, tag2, tag3

REGULAR:
tag1, tag2, tag3"""

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
                
            if line.startswith('CATEGORY:'):
                current_section = 'category'
            elif line.startswith('IMPORTANT:'):
                current_section = 'important'
            elif line.startswith('REGULAR:'):
                current_section = 'regular'
            elif line.startswith('- ') and current_section == 'category':
                category = line[2:].strip()
            elif current_section in ['important', 'regular'] and line:
                tags = [tag.strip() for tag in line.split(',') if tag.strip()]
                if current_section == 'important':
                    important_tags.extend(tags)
                else:
                    regular_tags.extend(tags)
        
        return list(dict.fromkeys(important_tags))[:8], list(dict.fromkeys(regular_tags))[:12], category

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
        """Validate product recommendations using AI."""
        if not products:
            return []
            
        formatted_products = []
        for i, product in enumerate(products[:10], 1):
            formatted_products.append(f"{i}. {product.get('product_id', 'N/A')}: {product.get('title', 'N/A')}")
        
        prompt = f"""Validate these product recommendations for the user query.

USER QUERY: {user_query}
PRODUCTS: {chr(10).join(formatted_products)}

Return ONLY valid product IDs in format: PROD001, PROD002
If no matches: NO_MATCHES"""

        try:
            response = self._call_ai(prompt)
            if "NO_MATCHES" in response.upper():
                return []
            
            import re
            product_ids = re.findall(r'PROD\d+', response.upper())
            return list(dict.fromkeys(product_ids))[:5]
        except Exception as e:
            print(f"Error in validation: {e}")
            return [p.get('product_id') for p in products[:3] if p.get('product_id')]

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
        
        important_tags, regular_tags, category_name = self.convert_to_searchable_tags(tags)
        
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