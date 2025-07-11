# CLIP Clothing Classifier Class
# Install required packages first:
# !pip install torch torchvision clip-by-openai pillow

import torch
import clip
from PIL import Image

class ClothingClassifier:
    def __init__(self):
        """Initialize the CLIP model and categories"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        
        # Topwear categories
        self.topwear = [
            "t-shirt", "shirt", "blouse", "tank top", "polo shirt", "dress shirt",
            "sweater", "hoodie", "jacket", "blazer", "coat", "cardigan", 
            "vest", "crop top", "tube top", "halter top", "camisole"
        ]
        
        # Bottomwear categories  
        self.bottomwear = [
            "jeans", "pants", "trousers", "shorts", "skirt", "leggings",
            "sweatpants", "chinos", "cargo pants", "dress pants", "joggers",
            "capris", "culottes", "palazzo pants", "wide leg pants"
        ]
        
        # Dresses and full outfits
        self.full_outfits = [
            "dress", "gown", "sundress", "maxi dress", "mini dress", 
            "cocktail dress", "evening dress", "jumpsuit", "romper", "overall"
        ]
        
        # Colors to test against
        self.colors = [
            "red", "blue", "green", "yellow", "orange", "purple", "pink",
            "black", "white", "gray", "brown", "navy", "beige", "khaki",
            "maroon", "teal", "olive", "cream", "gold", "silver", "denim blue"
        ]

        # Add these to your color list specifically for bottomwear
        self.bottomwear_colors = [
            "denim", "dark denim", "light denim", "faded denim", "black denim",
            "dark blue", "light blue", "navy blue", "stone blue",
            "charcoal", "dark gray", "light gray", "brown"
            "khaki", "tan khaki", "dark khaki", "olive green",
            "black", "dark black", "faded black"
        ]

        self.skin_shades = [
            "fair", "brown", "ashy", "red"
        ]
    
    def classify_image(self, image_path, verbose=False):
        """
        Classify clothing and skin color from image path
        
        Args:
            image_path (str): Path to the image file
            verbose (bool): Whether to print detailed analysis
            
        Returns:
            dict: Classification results with topwear, bottomwear, and skin color
        """
        try:
            # Load and preprocess the image
            image = Image.open(image_path).convert('RGB')
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            if verbose:
                print(f"Analyzing full body image: {image_path}")
                print("=" * 60)

            # ==== SKIN COLOR DETECTION =====
            skin_prompt = [f"person skin color is {color}" for color in self.skin_shades]
            skin_inputs = clip.tokenize(skin_prompt).to(self.device)

            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                skin_features = self.model.encode_text(skin_inputs)
                
                # Normalize features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                skin_features = skin_features / skin_features.norm(dim=-1, keepdim=True)
            
                # Calculate similarities
                skin_similarities = (image_features @ skin_features.T).softmax(dim=-1)
                
                # Get top 3 skin shade predictions
                skin_probs, skin_indices = skin_similarities[0].topk(3)
                
                if verbose:
                    print("SKIN SHADES:")
                skin_shade_results = []
                for i in range(3):
                    item = self.skin_shades[skin_indices[i]]
                    confidence = skin_probs[i].item()
                    if verbose:
                        print(f"   {item}: {confidence:.3f} ({confidence*100:.1f}%)")
                    skin_shade_results.append((item, confidence))
            
            # ===== TOPWEAR DETECTION =====
            top_prompts = [f"person wearing {item}" for item in self.topwear]
            top_inputs = clip.tokenize(top_prompts).to(self.device)
            
            with torch.no_grad():
                top_features = self.model.encode_text(top_inputs)
                
                # Normalize features
                top_features = top_features / top_features.norm(dim=-1, keepdim=True)
                
                # Calculate similarities
                top_similarities = (image_features @ top_features.T).softmax(dim=-1)
                
                # Get top 3 topwear predictions
                top_probs, top_indices = top_similarities[0].topk(3)
                
                if verbose:
                    print("👕 TOPWEAR:")
                topwear_results = []
                for i in range(3):
                    item = self.topwear[top_indices[i]]
                    confidence = top_probs[i].item()
                    if verbose:
                        print(f"   {item}: {confidence:.3f} ({confidence*100:.1f}%)")
                    topwear_results.append((item, confidence))
            
            # ===== BOTTOMWEAR DETECTION =====
            bottom_prompts = [f"person wearing {item}" for item in self.bottomwear]
            bottom_inputs = clip.tokenize(bottom_prompts).to(self.device)
            
            with torch.no_grad():
                bottom_features = self.model.encode_text(bottom_inputs)
                bottom_features = bottom_features / bottom_features.norm(dim=-1, keepdim=True)
                
                # Calculate similarities
                bottom_similarities = (image_features @ bottom_features.T).softmax(dim=-1)
                
                # Get top 3 bottomwear predictions
                bottom_probs, bottom_indices = bottom_similarities[0].topk(3)
                
                if verbose:
                    print("\n👖 BOTTOMWEAR:")
                bottomwear_results = []
                for i in range(3):
                    item = self.bottomwear[bottom_indices[i]]
                    confidence = bottom_probs[i].item()
                    if verbose:
                        print(f"   {item}: {confidence:.3f} ({confidence*100:.1f}%)")
                    bottomwear_results.append((item, confidence))
            
            # ===== FULL OUTFIT CHECK =====
            outfit_prompts = [f"person wearing {item}" for item in self.full_outfits]
            outfit_inputs = clip.tokenize(outfit_prompts).to(self.device)
            
            with torch.no_grad():
                outfit_features = self.model.encode_text(outfit_inputs)
                outfit_features = outfit_features / outfit_features.norm(dim=-1, keepdim=True)
                
                # Calculate similarities
                outfit_similarities = (image_features @ outfit_features.T).softmax(dim=-1)
                
                # Get top outfit prediction
                outfit_prob, outfit_index = outfit_similarities[0].topk(1)
                
                best_outfit = self.full_outfits[outfit_index[0]]
                outfit_confidence = outfit_prob[0].item()
                
                if verbose:
                    print(f"\n👗 FULL OUTFIT CHECK:")
                    print(f"   {best_outfit}: {outfit_confidence:.3f} ({outfit_confidence*100:.1f}%)")
            
            # ===== IMPROVED COLOR DETECTION =====
            if verbose:
                print(f"\n🎨 COLORS:")
            
            # Method 1: Direct color detection for specific clothing items
            best_top = topwear_results[0][0]
            best_bottom = bottomwear_results[0][0]
            
            # Top color detection with specific clothing item
            top_color_prompts = [f"person wearing {color} {best_top}" for color in self.colors]
            top_color_inputs = clip.tokenize(top_color_prompts).to(self.device)
            
            # Bottom color detection with specific clothing item
            bottom_color_prompts = [f"person wearing {color} {best_bottom}" for color in self.bottomwear_colors]
            bottom_color_inputs = clip.tokenize(bottom_color_prompts).to(self.device)
            
            with torch.no_grad():
                top_color_features = self.model.encode_text(top_color_inputs)
                bottom_color_features = self.model.encode_text(bottom_color_inputs)
                
                top_color_features = top_color_features / top_color_features.norm(dim=-1, keepdim=True)
                bottom_color_features = bottom_color_features / bottom_color_features.norm(dim=-1, keepdim=True)
                
                # Calculate color similarities
                top_color_sims = (image_features @ top_color_features.T).softmax(dim=-1)
                bottom_color_sims = (image_features @ bottom_color_features.T).softmax(dim=-1)
                
                # Get top 3 colors for each
                top_color_probs, top_color_indices = top_color_sims[0].topk(3)
                bottom_color_probs, bottom_color_indices = bottom_color_sims[0].topk(3)
                
                if verbose:
                    print(f"   Topwear ({best_top}):")
                top_color_results = []
                for i in range(3):
                    color = self.colors[top_color_indices[i]]
                    confidence = top_color_probs[i].item()
                    if verbose:
                        print(f"     {color}: {confidence:.3f} ({confidence*100:.1f}%)")
                    top_color_results.append((color, confidence))
                    
                if verbose:
                    print(f"   Bottomwear ({best_bottom}):")
                bottom_color_results = []
                for i in range(3):
                    color = self.colors[bottom_color_indices[i]]
                    confidence = bottom_color_probs[i].item()
                    if verbose:
                        print(f"     {color}: {confidence:.3f} ({confidence*100:.1f}%)")
                    bottom_color_results.append((color, confidence))
            
            # Method 2: Alternative detection with different prompts
            if verbose:
                print(f"\n🔍 ALTERNATIVE COLOR CHECK:")
            
            # Try with "wearing" vs "has" prompts
            alt_top_prompts = [f"{color} {best_top}" for color in self.colors]
            alt_bottom_prompts = [f"{color} {best_bottom}" for color in self.colors]
            
            alt_top_inputs = clip.tokenize(alt_top_prompts).to(self.device)
            alt_bottom_inputs = clip.tokenize(alt_bottom_prompts).to(self.device)
            
            with torch.no_grad():
                alt_top_features = self.model.encode_text(alt_top_inputs)
                alt_bottom_features = self.model.encode_text(alt_bottom_inputs)
                
                alt_top_features = alt_top_features / alt_top_features.norm(dim=-1, keepdim=True)
                alt_bottom_features = alt_bottom_features / alt_bottom_features.norm(dim=-1, keepdim=True)
                
                alt_top_sims = (image_features @ alt_top_features.T).softmax(dim=-1)
                alt_bottom_sims = (image_features @ alt_bottom_features.T).softmax(dim=-1)
                
                alt_top_prob, alt_top_idx = alt_top_sims[0].topk(1)
                alt_bottom_prob, alt_bottom_idx = alt_bottom_sims[0].topk(1)
                
                alt_top_color = self.colors[alt_top_idx[0]]
                alt_bottom_color = self.colors[alt_bottom_idx[0]]
                
                if verbose:
                    print(f"   Alternative top color: {alt_top_color} ({alt_top_prob[0].item()*100:.1f}%)")
                    print(f"   Alternative bottom color: {alt_bottom_color} ({alt_bottom_prob[0].item()*100:.1f}%)")
            
            # Choose best colors (highest confidence)
            final_top_color = top_color_results[0][0]
            final_bottom_color = bottom_color_results[0][0]
            
            # Use alternative if much more confident
            if alt_top_prob[0].item() > top_color_results[0][1] + 0.1:
                final_top_color = alt_top_color
            if alt_bottom_prob[0].item() > bottom_color_results[0][1] + 0.1:
                final_bottom_color = alt_bottom_color
            
            # ===== FINAL DESCRIPTION =====
            best_top = topwear_results[0][0]
            best_bottom = bottomwear_results[0][0]
            
            # Check if it's more likely a dress/full outfit
            if outfit_confidence > 0.3:  # If dress/outfit confidence is high
                # For dresses, use the top color detection
                dress_color = final_top_color
                description = f"{dress_color} {best_outfit}"
                outfit_type = "full_outfit"
            else:
                description = f"{final_top_color} {best_top} and {final_bottom_color} {best_bottom}"
                outfit_type = "separates"
            
            if verbose:
                print(f"\n📝 FINAL OUTFIT DESCRIPTION:")
                print(f"   {description}")
            
            return {
                'topwear': topwear_results,
                'bottomwear': bottomwear_results,
                'skin_color': skin_shade_results,
                'full_outfit': (best_outfit, outfit_confidence),
                'top_color': final_top_color,
                'bottom_color': final_bottom_color,
                'top_color_options': top_color_results,
                'bottom_color_options': bottom_color_results,
                'description': description,
                'type': outfit_type
            }
                
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    
    def get_simple_tags(self, image_path):
        """
        Get simple tags without verbose output
        
        Returns:
            dict: Simple tags with best predictions
        """
        result = self.classify_image(image_path, verbose=False)
        if result:
            return {
                'topwear': result['topwear'][0][0],
                'bottomwear': result['bottomwear'][0][0], 
                'skin_color': result['skin_color'][0][0],
                'top_color': result['top_color'],
                'bottom_color': result['bottom_color'],
                'description': result['description']
            }
        return None

# Example usage:
if __name__ == "__main__":
    # Initialize the classifier
    classifier = ClothingClassifier()
    
    # Example image path
    image_path = "images/person6.jpeg"  # Change this to your actual image path
    
    print("CLIP Clothing Classifier")
    print("=" * 50)
    
    # Get detailed analysis
    results = classifier.classify_image(image_path, verbose=True)
    
    if results:
        print(f"\n✨ Final Result: {results['description']}")
    
    # Get simple tags
    print("\n" + "="*50)
    print("SIMPLE TAGS:")
    simple_tags = classifier.get_simple_tags(image_path)
    if simple_tags:
        print(f"Topwear: {simple_tags['topwear']}")
        print(f"Bottomwear: {simple_tags['bottomwear']}")
        print(f"Skin Color: {simple_tags['skin_color']}")
        print(f"Description: {simple_tags['description']}")

# Usage from other places:
# classifier = ClothingClassifier()
# tags = classifier.get_simple_tags("path/to/image.jpg")
# print(tags['topwear'], tags['bottomwear'], tags['skin_color'])