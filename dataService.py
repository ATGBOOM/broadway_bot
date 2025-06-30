import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

class ProductDataService:
    def __init__(self, json_file_path = "fashion_ai_training_data.json"):
        """
        Initialize the Product Data Service
        
        Args:
            json_file_path (str): Path to the JSON file containing product data
        """
        self.json_file_path = json_file_path
        self.data = {}
        self.metadata = {}
        self.categories = {}
        self.brands = {}
        self.products = {}
        self.customers = {}
        self.search_indices = {}
        self.ai_training_context = {}
        
        self.load_data()
    
    def load_data(self) -> bool:
        """
        Load product data from JSON file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.json_file_path):
                print(f"❌ Error: File '{self.json_file_path}' not found")
                return False
            
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                self.data = json.load(file)
            
            # Extract main data sections
            self.metadata = self.data.get('metadata', {})
            self.categories = self.data.get('categories', {})
            self.brands = self.data.get('brands', {})
            self.products = self.data.get('products', {})
            self.customers = self.data.get('customers', {})
            self.search_indices = self.data.get('search_indices', {})
            self.ai_training_context = self.data.get('ai_training_context', {})
            
            print(f"✅ Successfully loaded product data from '{self.json_file_path}'")
            print(f"📊 Total products: {self.metadata.get('total_products', 0)}")
            print(f"🏢 Total brands: {self.metadata.get('total_brands', 0)}")
            print(f"👥 Total customers: {self.metadata.get('total_customers', 0)}")
            print(f"📂 Categories: {', '.join(self.metadata.get('categories', []))}")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON format in file '{self.json_file_path}'")
            print(f"Details: {e}")
            return False
            
        except Exception as e:
            print(f"❌ Error loading file '{self.json_file_path}': {e}")
            return False
    
    def get_categories_available(self) -> Dict[str, Any]:
        """
        Get all available categories
        
        Returns:
            dict: Categories information
        """
        categories_list = list(self.categories.keys())
        
        return {
            "total_categories": len(categories_list),
            "categories": categories_list,
            "categories_detail": {
                category: {
                    "subcategories": list(subcats.keys()),
                    "total_subcategories": len(subcats),
                    "total_products": sum(len(products) for products in subcats.values())
                }
                for category, subcats in self.categories.items()
            },
            "metadata": {
                "last_updated": self.metadata.get('generated_date'),
                "source": "product_database"
            }
        }
    
   
    def get_subcategories_available(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all available subcategories, optionally filtered by category
        
        Args:
            category (str, optional): Filter by specific category
            
        Returns:
            dict: Subcategories information
        """
        if category and category in self.categories:
            # Get subcategories for specific category
            subcats = self.categories[category]
            return {
                "category": category,
                "total_subcategories": len(subcats),
                "subcategories": list(subcats.keys()),
                "subcategories_detail": {
                    subcat: {
                        "total_products": len(products),
                        "product_ids": [p.get('product_id') for p in products]
                    }
                    for subcat, products in subcats.items()
                }
            }
        else:
            # Get all subcategories across all categories
            all_subcats = {}
            for cat_name, subcats in self.categories.items():
                for subcat_name, products in subcats.items():
                    all_subcats[f"{cat_name}_{subcat_name}"] = {
                        "category": cat_name,
                        "subcategory": subcat_name,
                        "total_products": len(products),
                        "product_ids": [p.get('product_id') for p in products]
                    }
            
            return {
                "total_subcategories": len(all_subcats),
                "subcategories": all_subcats,
                "by_category": {
                    cat: list(subcats.keys()) 
                    for cat, subcats in self.categories.items()
                }
            }
    
    def get_consumer_information(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get consumer/customer information
        
        Args:
            customer_id (str, optional): Get specific customer data
            
        Returns:
            dict: Customer information
        """
        if customer_id and customer_id in self.customers:
            # Get specific customer data
            customer = self.customers[customer_id]
            return {
                "customer_id": customer_id,
                "customer_data": customer,
                "purchase_history": self._get_customer_purchase_history(customer_id),
                "review_history": self._get_customer_review_history(customer_id),
                "preferences": self._analyze_customer_preferences(customer_id)
            }
        else:
            # Get overview of all customers
            customer_overview = {
                "total_customers": len(self.customers),
                "customer_ids": list(self.customers.keys()),
                "customer_demographics": self._analyze_customer_demographics(),
                "customer_insights": self.ai_training_context.get('customer_insights', {}),
                "active_customers": self._get_active_customers(),
                "top_customers": self._get_top_customers()
            }
            
            return customer_overview
    
    def get_product_data(self, product_id: Optional[str] = None, 
                        category: Optional[str] = None, 
                        subcategory: Optional[str] = None) -> Dict[str, Any]:
        """
        Get product data with various filters
        
        Args:
            product_id (str, optional): Get specific product
            category (str, optional): Filter by category
            subcategory (str, optional): Filter by subcategory
            
        Returns:
            dict: Product information
        """
        if product_id:
            # Get specific product data
            product = self._find_product_by_id(product_id)
            if product:
                return {
                    "product_id": product_id,
                    "product_data": product,
                    "category_info": self._get_product_category_info(product_id),
                    "brand_info": self._get_product_brand_info(product.get('brand_id')),
                    "related_products": {
                        "alternatives": product.get('alternatives', []),
                        "complements": product.get('complements', [])
                    },
                    "analytics": {
                        "total_orders": len(product.get('orders', [])),
                        "total_reviews": len(product.get('reviews', [])),
                        "average_rating": product.get('average_rating', 0)
                    }
                }
            else:
                return {"error": f"Product {product_id} not found"}
        
        elif category and subcategory:
            # Get products by category and subcategory
            if category in self.categories and subcategory in self.categories[category]:
                products = self.categories[category][subcategory]
                return {
                    "category": category,
                    "subcategory": subcategory,
                    "total_products": len(products),
                    "products": products,
                    "summary": self._get_category_summary(category, subcategory)
                }
            else:
                return {"error": f"Category '{category}' or subcategory '{subcategory}' not found"}
        
        elif category:
            # Get all products in category
            if category in self.categories:
                all_products = []
                for subcategory, products in self.categories[category].items():
                    all_products.extend(products)
                
                return {
                    "category": category,
                    "total_products": len(all_products),
                    "subcategories": list(self.categories[category].keys()),
                    "products": all_products,
                    "summary": self._get_category_summary(category)
                }
            else:
                return {"error": f"Category '{category}' not found"}
        
        else:
            # Get overview of all products
            return {
                "total_products": len(self.products),
                "products_by_category": {
                    cat: sum(len(products) for products in subcats.values())
                    for cat, subcats in self.categories.items()
                },
                "popular_products": self.ai_training_context.get('popular_products', []),
                "trending_categories": self.ai_training_context.get('trending_categories', []),
                "price_ranges": self.search_indices.get('by_price_range', {}),
                "available_tags": list(self.search_indices.get('by_tags', {}).keys())
            }
    
    def get_complete_data_summary(self) -> Dict[str, Any]:
        """
        Get a complete summary of all available data
        
        Returns:
            dict: Complete data summary
        """
        return {
            "metadata": self.metadata,
            "data_summary": {
                "categories": self.get_categories_available(),
                "products_overview": self.get_product_data(),
                "customers_overview": self.get_consumer_information(),
                "brands_summary": self._get_brands_summary()
            },
            "search_capabilities": {
                "available_indices": list(self.search_indices.keys()),
                "search_by_category": bool(self.search_indices.get('by_category')),
                "search_by_brand": bool(self.search_indices.get('by_brand')),
                "search_by_price": bool(self.search_indices.get('by_price_range')),
                "search_by_tags": bool(self.search_indices.get('by_tags'))
            },
            "ai_context": self.ai_training_context,
            "last_updated": self.metadata.get('generated_date', 'Unknown')
        }
    
    # Helper methods
    def _find_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Find a product by ID across all categories"""
        if product_id in self.products:
            return self.products[product_id]
        
        # Search in categories structure
        for category, subcategories in self.categories.items():
            for subcategory, products in subcategories.items():
                for product in products:
                    if product.get('product_id') == product_id:
                        return product
        return None
    
    def _get_customer_purchase_history(self, customer_id: str) -> List[Dict]:
        """Get purchase history for a customer"""
        purchases = []
        for category, subcategories in self.categories.items():
            for subcategory, products in subcategories.items():
                for product in products:
                    for order in product.get('orders', []):
                        if order.get('customer_id') == customer_id:
                            purchases.append({
                                "order_id": order.get('order_id'),
                                "product_id": product.get('product_id'),
                                "product_title": product.get('title'),
                                "price": product.get('price'),
                                "category": category,
                                "subcategory": subcategory
                            })
        return purchases
    
    def _get_customer_review_history(self, customer_id: str) -> List[Dict]:
        """Get review history for a customer"""
        reviews = []
        for category, subcategories in self.categories.items():
            for subcategory, products in subcategories.items():
                for product in products:
                    for review in product.get('reviews', []):
                        if review.get('customer_id') == customer_id:
                            reviews.append({
                                "product_id": product.get('product_id'),
                                "product_title": product.get('title'),
                                "rating": review.get('rating'),
                                "review_text": review.get('review_text'),
                                "category": category
                            })
        return reviews
    
    def _analyze_customer_preferences(self, customer_id: str) -> Dict[str, Any]:
        """Analyze customer preferences based on purchase and review history"""
        purchases = self._get_customer_purchase_history(customer_id)
        reviews = self._get_customer_review_history(customer_id)
        
        # Analyze preferred categories
        category_counts = {}
        for purchase in purchases:
            category = purchase['category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Analyze price range
        prices = [purchase['price'] for purchase in purchases if purchase.get('price')]
        avg_price = sum(prices) / len(prices) if prices else 0
        
        return {
            "preferred_categories": sorted(category_counts.items(), key=lambda x: x[1], reverse=True),
            "total_purchases": len(purchases),
            "total_reviews": len(reviews),
            "average_purchase_price": round(avg_price, 2),
            "price_range": {"min": min(prices) if prices else 0, "max": max(prices) if prices else 0},
            "average_rating_given": round(sum(r['rating'] for r in reviews) / len(reviews), 1) if reviews else 0
        }
    
    def _analyze_customer_demographics(self) -> Dict[str, Any]:
        """Analyze overall customer demographics"""
        total_customers = len(self.customers)
        
        # Get customer activity
        active_customers = len([cid for cid in self.customers.keys() 
                              if len(self._get_customer_purchase_history(cid)) > 0])
        
        return {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "customer_engagement_rate": round((active_customers / total_customers) * 100, 1) if total_customers > 0 else 0
        }
    
    def _get_active_customers(self) -> List[str]:
        """Get list of active customers (those with purchases)"""
        active = []
        for customer_id in self.customers.keys():
            if len(self._get_customer_purchase_history(customer_id)) > 0:
                active.append(customer_id)
        return active[:10]  # Return top 10
    
    def _get_top_customers(self) -> List[Dict]:
        """Get top customers by purchase count"""
        customer_purchases = []
        for customer_id in self.customers.keys():
            purchases = self._get_customer_purchase_history(customer_id)
            if purchases:
                customer_purchases.append({
                    "customer_id": customer_id,
                    "total_purchases": len(purchases),
                    "total_spent": sum(p.get('price', 0) for p in purchases)
                })
        
        return sorted(customer_purchases, key=lambda x: x['total_purchases'], reverse=True)[:5]
    
    def _get_product_category_info(self, product_id: str) -> Dict[str, str]:
        """Get category information for a product"""
        for category, subcategories in self.categories.items():
            for subcategory, products in subcategories.items():
                for product in products:
                    if product.get('product_id') == product_id:
                        return {"category": category, "subcategory": subcategory}
        return {}
    
    def _get_product_brand_info(self, brand_id: str) -> Dict[str, Any]:
        """Get brand information"""
        return self.brands.get(brand_id, {})
    
    def _get_category_summary(self, category: str, subcategory: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for a category/subcategory"""
        if subcategory:
            products = self.categories.get(category, {}).get(subcategory, [])
        else:
            products = []
            for subcat_products in self.categories.get(category, {}).values():
                products.extend(subcat_products)
        
        if not products:
            return {}
        
        prices = [p.get('price', 0) for p in products]
        ratings = [p.get('average_rating', 0) for p in products if p.get('average_rating')]
        
        return {
            "total_products": len(products),
            "price_range": {"min": min(prices), "max": max(prices)} if prices else {},
            "average_price": round(sum(prices) / len(prices), 2) if prices else 0,
            "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0,
            "brands_available": len(set(p.get('brand_id') for p in products if p.get('brand_id')))
        }
    
    def _get_brands_summary(self) -> Dict[str, Any]:
        """Get summary of all brands"""
        return {
            "total_brands": len(self.brands),
            "brand_ids": list(self.brands.keys()),
            "brands_detail": self.brands,
            "brand_index": self.search_indices.get('by_brand', {})
        }

# Usage functions
def initialize_product_service(json_file_path: str) -> Optional['ProductDataService']:
    """
    Initialize ProductDataService with error handling
    
    Args:
        json_file_path (str): Path to JSON file
        
    Returns:
        ProductDataService or None: Service instance if successful
    """
    try:
        service = ProductDataService(json_file_path)
        return service if service.data else None
    except Exception as e:
        print(f"❌ Failed to initialize ProductDataService: {e}")
        return None

def main():
    """Example usage of ProductDataService"""
    # Initialize service
    json_file = "fashion_ai_training_data.json"  # Update with your file path
    service = initialize_product_service(json_file)
    
    if not service:
        print("❌ Failed to initialize service")
        return
    
    print("\n=== PRODUCT DATA SERVICE DEMO ===")
    
    # Test categories
    print("\n📂 CATEGORIES:")
    categories = service.get_categories_available()
    print(categories)
    
    # # Test subcategories
    # print("\n📁 SUBCATEGORIES:")
    # subcats = service.get_subcategories_available("Clothing")
    # print(f"Clothing subcategories: {subcats.get('subcategories', [])}")
    
    # # Test customer info
    # print("\n👥 CUSTOMER INFO:")
    # customers = service.get_consumer_information()
    # print(f"Total customers: {customers['total_customers']}")
    # print(f"Active customers: {len(customers.get('active_customers', []))}")
    
    # # Test product data
    # print("\n📦 PRODUCT DATA:")
    # products = service.get_product_data(category="Clothing", subcategory="Jeans")
    # print(f"Jeans products: {products.get('total_products', 0)}")
    
    # # Test complete summary
    # print("\n📊 COMPLETE SUMMARY:")
    # summary = service.get_complete_data_summary()
    # print(f"Last updated: {summary['last_updated']}")
    # print(f"Search capabilities: {list(summary['search_capabilities'].keys())}")

if __name__ == "__main__":
    main()