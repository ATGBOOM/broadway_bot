import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from clothingClassifier import ClothingClassifier
import json

# Structured Output Models
class StyleCompatibilityAnalysis(BaseModel):
    """Analysis of how well a product suits the user"""
    overall_compatibility: str = Field(
        description="Overall assessment: excellent, good, fair, or poor"
    )

    body_type_match: bool = Field(
        description="Whether the item flatters the user's body type"
    )
    color_harmony: bool = Field(
        description="Whether the color complements the user's skin tone"
    )
    style_alignment: bool = Field(
        description="Whether it matches the user's style preferences"
    )

class StylingRecommendations(BaseModel):
    """Styling tips and recommendations"""
    styling_tips: List[str] = Field(
        description="Specific styling tips",
        min_items=3,
        max_items=15
    )
    fit_adjustments: List[str] = Field(
        description="Suggested fit modifications or styling tricks"
    )
    complementary_pieces: List[str] = Field(
        description="Types of items that would complete the look"
    )
    occasion_suitability: List[str] = Field(
        description="Occasions where this styling would work well"
    )

class LooksGoodOnMeResponse(BaseModel):
    """Complete response from the LooksGoodOnMe service"""
    compatibility_analysis: StyleCompatibilityAnalysis
    styling_recommendations: StylingRecommendations
    summary: str = Field(
        description="Brief summary for the user"
    )
    what_works : str = Field(
        description="What parts of the outfit looks good"
    )

    improvement : str = Field(
        description="what areas of outfit could be improved"
    )
   

    should_recommend_alternatives: bool = Field(
        description="Whether the recommendation service should find alternatives"
    )

class InferredProductDetails(BaseModel):
    """Model for product details inferred from conversation"""
    type: str = Field(description="Type of clothing item (dress, shirt, pants, etc.)")
    color: str = Field(description="Primary color mentioned or inferred")
    description: str = Field(description="Descriptive details about the item")
    brand_name: Optional[str] = Field(description="Brand if mentioned", default="inferred")
    price: Optional[str] = Field(description="Price if mentioned", default="not specified")
    style_attributes: List[str] = Field(description="Style descriptors", default=[])
   

class LooksGoodOnMeService:
    """
    Service that analyzes if products look good on users and provides styling tips
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.3
        )

        self.clothing_classifier = ClothingClassifier()
        
        self.parser = PydanticOutputParser(pydantic_object=LooksGoodOnMeResponse)
        self.inference_parser = PydanticOutputParser(pydantic_object=InferredProductDetails)
        self._setup_analysis_chain()
        self._setup_inference_chain()
    
    def _setup_analysis_chain(self):
        """Setup the main analysis chain using LCEL"""
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are Broadway's expert fashion stylist AI. Your job is to analyze if clothing items look good on users and provide actionable styling advice.

Your analysis should consider:
1. **Body Type Compatibility**: How the item's silhouette works with the user's body type
2. **Color Harmony**: How the color complements the user's skin tone and preferences  
3. **Style Alignment**: How well it matches their personal style and lifestyle
4. **Fit & Proportion**: How to make the item work best for their body
5. **Versatility**: How to style it for different occasions

IMPORTANT: Your styling tips will be used as search tags to find complementary products, so make them specific and searchable (e.g., "cropped blazer", "nude heels", "delicate jewelry", "high-waisted", "oversized").

{format_instructions}"""),
            
            ("human", """Analyze this styling scenario:

**User Query:** {user_input}

**Conversation Context:** {conversation_context}

**User Information:**
- Body Type: {body_type}
- Skin Tone: {skin_tone} 
- Height: {height}
- Style Preferences: {style_preferences}
- Lifestyle: {lifestyle}
- Occasion Context: {occasion_context}
- Size Preferences: {size_preferences}

**Product Being Analyzed:**
- Type: {product_type}
- Color: {product_color}
- Description: {product_description}


Please provide a comprehensive styling analysis including specific styling tips that can be used to find complementary products.""")
        ])
        
        # Create the analysis chain
        self.analysis_chain = (
            analysis_prompt.partial(format_instructions=self.parser.get_format_instructions())
            | self.llm 
            | self.parser
        )
    
    def _setup_inference_chain(self):
        """Fixed inference chain with better prompt and error handling"""
        
        inference_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a product inference expert. Your job is to figure out what specific clothing item a user is referring to when they don't explicitly state it.

    Analyze all available information like a detective:
    1. Look for direct product mentions in the query
    2. Identify pronouns (this, that, it) and what they reference  
    3. Use conversation context to understand the topic
    4. Match user query to recent recommendations
    5. Make logical inferences about missing details

    CRITICAL: You must respond ONLY with valid JSON in the exact format specified. Do not include any explanatory text, narrative, or reasoning outside the JSON structure.

    {format_instructions}"""),
            
            ("human", """Analyze this scenario and infer the product details. Return ONLY the JSON response:

    **User's Current Query:** {user_input}
    **Conversation Context:** {conversation_context}  
    **Recent Recommendations:** {recent_recs}

    Extract the product details the user is asking about and return as JSON:""")
        ])
        
        # Fixed: Use inference_parser for both format instructions AND parsing
        self.inference_chain = (
            inference_prompt.partial(format_instructions=self.inference_parser.get_format_instructions())
            | self.llm
            | self.inference_parser
        )
   

    async def analyze_looks_good_on_me(
        self, 
        user_input: str,
        conversation_context: str,
        user_info: Dict[str, Any],
        product_details: Dict[str, Any],
        recs : List = None,
        image : str = None
    ) -> Dict[str, Any]:
        """
        Main analysis method that integrates with your Broadway system
        
        Args:
            user_input: The user's question/request
            conversation_context: Context from previous conversation
            user_info: User information from LangGraph state
            product_details: Details about the product being analyzed
        
        Returns:
            Analysis results including styling tips for recommendation service
        """
        
        try:

            if image:
                tags = await self.clothing_classifier.get_simple_tags(image)
                product_details = {
                    "type" : f"{tags['topwear']}, {tags['bottomwear']}",
                    "color" : f"{tags['top_color']}, {tags['bottom_color']}",
                    "description" : tags['description']
                }

            if not product_details or product_details.get("type") == "unknown":
                inference_data = {
                    "user_input": user_input,
                    "conversation_context": conversation_context,
                    "recent_recs": recs,
                }
                inference_result = self.inference_chain.invoke(inference_data)
                product_details = {
                    "type": inference_result.type,
                    "color": inference_result.color,
                    "description": inference_result.description,

                }
                
            # Prepare input for the analysis chain
            print("looks good on me bot", user_input, user_info, conversation_context)
            chain_input = {
                "user_input": user_input,
                "conversation_context": conversation_context,
                
                # User information (with defaults)
                "body_type": user_info.get("body_type", "not specified"),
                "skin_tone": user_info.get("skin_tone", "not specified"),
                "height": user_info.get("height", "not specified"),
                "style_preferences": ", ".join(user_info.get("style_preferences", ["versatile"])),
                "lifestyle": user_info.get("lifestyle", "not specified"),
                "occasion_context": user_info.get("current_occasion", "general wear"),
                "size_preferences": user_info.get("size_preferences", "regular fit"),
                "gender" : user_info.get("gender", "unknown"),

                # Product information (with defaults)
                "product_type": product_details.get("type", "clothing item"),
                "product_color": product_details.get("color", "not specified"),
                "product_description": product_details.get("description", ""),
            }
            
            # Run the analysis
            result = self.analysis_chain.invoke(chain_input)
            print(result)
            # Format response for your system
            return {
                "success": True,
                "analysis": result.model_dump(),
                
                # Extract styling tips for recommendation service
                "styling_tips_for_recommendations": result.styling_recommendations.styling_tips,
                "complementary_pieces": result.styling_recommendations.complementary_pieces,
                
                # User-facing response
                "user_response": {
                    "summary": result.summary,
                    "stlying_tips": result.styling_recommendations.styling_tips,
                    "adjustments": result.styling_recommendations.fit_adjustments,
                    "complementary_pieces": result.styling_recommendations.complementary_pieces,
                    "what_works" : result.what_works,
                    "improvement" : result.improvement
                },
                
                
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "styling_tips_for_recommendations": [],
                "user_response": {
                    "summary": "I apologize, but I encountered an issue analyzing this item. Could you provide more details?",
                    "detailed_feedback": f"Error: {str(e)}",
                    "compatibility_score": 5,
                    "overall_assessment": "unclear"
                }
            }
    
    def get_styling_tags_for_recommendations(
        self,
        styling_tips: List[str],
        complementary_pieces: List[str],
        user_style_preferences: List[str]
    ) -> List[str]:
        """
        Convert styling recommendations into search tags for your recommendation service
        This method processes the styling tips to create optimal search tags
        """
        
        # Combine all styling elements
        all_tags = []
        
        # Add styling tips (these are already optimized for search)
        all_tags.extend(styling_tips)
        
        # Add complementary pieces
        all_tags.extend(complementary_pieces)
        
        # Add user style preferences for context
        all_tags.extend(user_style_preferences)
        
        # Remove duplicates while preserving order
        unique_tags = []
        seen = set()
        for tag in all_tags:
            tag_clean = tag.lower().strip()
            if tag_clean not in seen and tag_clean:
                unique_tags.append(tag)
                seen.add(tag_clean)
        
        # Limit to reasonable number for search
        return unique_tags[:20]
    
    async def analyze_looks_good_on_me_async(
        self,
        user_input: str,
        conversation_context: str, 
        user_info: Dict[str, Any],
        product_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Async version for better performance in your LangGraph workflow"""
        
        try:
            chain_input = {
                "user_input": user_input,
                "conversation_context": conversation_context,
                "body_type": user_info.get("body_type", "not specified"),
                "skin_tone": user_info.get("skin_tone", "not specified"),
                "height": user_info.get("height", "not specified"),
                "style_preferences": ", ".join(user_info.get("style_preferences", ["versatile"])),
                "lifestyle": user_info.get("lifestyle", "not specified"),
                "occasion_context": user_info.get("current_occasion", "general wear"),
                "size_preferences": user_info.get("size_preferences", "regular fit"),
                "product_type": product_details.get("type", "clothing item"),
                "product_color": product_details.get("color", "not specified"),
                "product_description": product_details.get("description", ""),
                "product_brand": product_details.get("brand_name", "not specified"),
                "product_price": product_details.get("price", "not specified")
            }
            
            result = await self.analysis_chain.ainvoke(chain_input)
            
            return {
                "success": True,
                "analysis": result.model_dump(),
                "styling_tips_for_recommendations": result.styling_recommendations.styling_tips,
                "complementary_pieces": result.styling_recommendations.complementary_pieces,
                "user_response": {
                    "summary": result.summary,
                    "detailed_feedback": result.detailed_feedback,
                    "compatibility_score": result.compatibility_analysis.confidence_score,
                    "overall_assessment": result.compatibility_analysis.overall_compatibility
                },
                "should_find_alternatives": result.should_recommend_alternatives,
                "confidence_score": result.compatibility_analysis.confidence_score
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "styling_tips_for_recommendations": [],
                "user_response": {
                    "summary": "I apologize, but I encountered an issue analyzing this item.",
                    "detailed_feedback": f"Error: {str(e)}",
                    "compatibility_score": 5,
                    "overall_assessment": "unclear"
                }
            }



# async def main():
#     service = LooksGoodOnMeService()
    
#     # Example input from your system
#     user_input = "Would this red dress look good on me for a funeral?"
#     conversation_context = "User is looking for funeral attire. Previously discussed avoiding white/cream colors."
    
#     user_info = {
#         "body_type": "athletic",
#         "skin_tone": "cool",
#         "height": "5'6",
#         "style_preferences": ["elegant", "classic", "feminine"],
#         "lifestyle": "professional",
#         "size_preferences": "fitted on top, flowy on bottom"
#     }
    
#     product_details = {
#         "type": "dress",
#         "color": "red",
#         "description": "A-line midi dress with three-quarter sleeves",
#         "brand_name": "Broadway Collection",
#         "price": "$89"
#     }
    
#     recs = [
#     {
#         "title": "Black Funeral Dress",
#         "brand_name": "Broadway",
#         "color": "black",
#         "type": "dress",
#         "tags": ["funeral", "black", "conservative", "midi"]
#     }
#     ]

#     # Run analysis
#     result = await service.analyze_looks_good_on_me(
#         user_input="Will this green jacket, jeans, and blue tshirt look good on me",
#         conversation_context="The user is seeking validation on whether the dress suit her, which aligns with the intent of styling advice focused on personal fit and color compatibility.",
#         user_info=user_info,
#         product_details={},#product_details
#         recs=[], #recs,
        
#     )
#     print(result)
    
#     print("=== STYLING ANALYSIS RESULT ===")
#     print(f"Success: {result['success']}")
#     print(f"User Response: {result['user_response']['summary']}")
#     print(f"Styling Tips for Recommendations: {result['styling_tips_for_recommendations']}")
#     print(f"Should Find Alternatives: {result['should_find_alternatives']}")
    
#     # Example of how your recommendation service would use this
#     if result['success']:
#         styling_tags = service.get_styling_tags_for_recommendations(
#             styling_tips=result['styling_tips_for_recommendations'],
#             complementary_pieces=result['complementary_pieces'],
#             user_style_preferences=user_info['style_preferences']
#         )
#         print(f"Final Tags for Recommendation Service: {styling_tags}")

# if __name__ == "__main__":
#     asyncio.run(main())