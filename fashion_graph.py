# fashion_graph.py - New file for LangGraph integration
from typing import Dict, List, Optional, Literal, TypedDict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


class FashionState(TypedDict):
    """State that flows through the LangGraph workflow"""
    user_input: str
    client_id: str
    conversation_history: str
    service_mode: Optional[str]
    gender: Optional[str]
    current_parameters: Optional[Dict]
    recommendations: List[Dict]
    response_message: Optional[str]  # Added to store the response message
    websocket_messages: List[Dict]
    follow_up_needed: bool
    follow_up_message: Optional[str]
    confidence_score: Optional[float]
    error_message: Optional[str]
    is_gender_loop: bool  

class FashionWorkflow:
    """LangGraph workflow for fashion bot conversations"""
    
    def __init__(self, services_dict):
        """Initialize with your existing services"""
        self.occasion_service = services_dict['occasion']
        self.recommendation_service = services_dict['recommendation']
        self.pairing_service = services_dict['pairing']
        self.vacation_service = services_dict['vacation']
        self.conversation_service = services_dict['conversation']
        self.general_service = services_dict['general']
        self.gender_service = services_dict['gender']
        
        # Build and compile the workflow
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile(checkpointer=MemorySaver())
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        workflow = StateGraph(FashionState)
        
        # Add nodes (each represents a step in your current logic)
        workflow.add_node("process_conversation", self._process_conversation)
        workflow.add_node("extract_gender", self._extract_gender)
        workflow.add_node("ask_for_gender", self._ask_for_gender)
        workflow.add_node("route_to_service", self._route_to_service)
        workflow.add_node("handle_occasion", self._handle_occasion)
        workflow.add_node("handle_pairing", self._handle_pairing)
        workflow.add_node("handle_vacation", self._handle_vacation)
        workflow.add_node("handle_general", self._handle_general)
        workflow.add_node("generate_followup", self._generate_followup)
        workflow.add_node("prepare_response", self._prepare_response)
        workflow.add_node("process_bot_response", self._process_bot_response)
        
        # Define the flow
        workflow.set_entry_point("process_conversation")
        
        # # Always extract gender after processing conversation
        workflow.add_edge("process_conversation", "extract_gender")
        
   
        workflow.add_conditional_edges(
            "extract_gender",
            self._check_gender_available,
            {
                "gender_found": "route_to_service",
                "gender_missing": "ask_for_gender"
            }
        )
        workflow.add_edge("ask_for_gender", "prepare_response")

        # workflow.add_edge("process_conversation", "route_to_service")
        
        # Conditional routing based on service mode
        workflow.add_conditional_edges(
            "route_to_service",
            self._decide_service_route,
            {
                "occasion": "handle_occasion",
                "pairing": "handle_pairing", 
                "vacation": "handle_vacation",
                "general": "handle_general"
            }
        )
        
        # Check if follow-up is needed after each service
        workflow.add_conditional_edges(
            "handle_occasion",
            self._check_followup_needed,
            {
                "followup": "generate_followup",
                "complete": "prepare_response"
            }
        )
        
        workflow.add_conditional_edges(
            "handle_pairing",
            self._check_followup_needed,
            {
                "followup": "generate_followup",
                "complete": "prepare_response"
            }
        )
        
        workflow.add_conditional_edges(
            "handle_vacation",
            self._check_followup_needed,
            {
                "followup": "generate_followup",
                "complete": "prepare_response"
            }
        )
        
        # General and followup always go to response preparation
        workflow.add_edge("handle_general", "prepare_response")
        workflow.add_edge("generate_followup", "prepare_response")
        
        # End the workflow
        workflow.add_edge("prepare_response", "process_bot_response")
        workflow.add_edge("process_bot_response", END)
        
        return workflow
    
    # Node implementations (wrapping your existing logic)
    
    def _process_conversation(self, state: FashionState) -> FashionState:
        """Process conversation using your existing conversation service"""
        try:
            intent, context = self.conversation_service.processTurn(state["user_input"], state['gender'])
            state["service_mode"] = intent.lower()
            state["conversation_history"] = context
            return state
        except Exception as e:
            state["error_message"] = f"Error processing conversation: {str(e)}"
            return state
    
    def _extract_gender(self, state: FashionState) -> FashionState:
        """Extract gender using your existing logic"""
        try:
            # Use your existing gender extraction logic
            gender = self._infer_gender(state["user_input"], state["conversation_history"], state['gender'])
            state["gender"] = gender
            return state
        except Exception as e:
            state["error_message"] = f"Error extracting gender: {str(e)}"
            return state
        
    def _ask_for_gender(self, state: FashionState) :
        """Ask user to specify their gender"""
        # Set a flag to indicate we're asking for gender
        state["is_gender_loop"] = True
        state["response_message"] = "I'd like to provide you with more personalized recommendations. Could you please let me know if this is for a man or woman"
        return state
    
    def _route_to_service(self, state: FashionState) -> FashionState:
        """Prepare for service routing"""
        # Just pass through - routing logic is in conditional edges
        return state
    
    def _handle_occasion(self, state: FashionState) -> FashionState:
        """Handle occasion mode using your existing logic"""
        try:
            # Extract parameters using your existing service
            parameters = self.occasion_service.extract_parameters(
                state["user_input"], 
                state.get("current_parameters"), 
                state["conversation_history"]
            )
            state["current_parameters"] = parameters
            
            # Check if we have enough info
            confidence_score = self.occasion_service.get_confidence_score(parameters)
            state["confidence_score"] = confidence_score
            
            occasion = parameters.get('core_parameters', {}).get('occasion') is not None
            
            if not state["gender"] or not occasion:
                state["follow_up_needed"] = True
                state["follow_up_message"] = "Could you tell me more about the occasion and whether this is for men or women?"
            else:
                # Generate recommendations
                dialogue, recommendations = self._generate_occasion_recommendations(state)
                state["recommendations"] = recommendations
                state["response_message"] = dialogue
                state["follow_up_needed"] = False
                
            return state
            
        except Exception as e:
            state["error_message"] = f"Error in occasion handling: {str(e)}"
            return state
    
    def _handle_pairing(self, state: FashionState) -> FashionState:
        """Handle pairing mode using your existing logic"""
        try:
            # Since we already checked gender in routing, we should have it
            # Get complementary products using your existing service
            complements = self.pairing_service.getComplementProducts(
                state["user_input"], 
                state["conversation_history"]
            )
            state["recommendations"] = complements
            
            # Generate response message for pairing
            item_to_pair = state["user_input"].lower().strip()
            if complements:
                response_message = f"Perfect! For {item_to_pair}, here are some great pieces that would complement it beautifully. These combinations will create cohesive, stylish looks!"
            else:
                response_message = f"I couldn't find specific pairings for '{item_to_pair}'. Could you try describing the item differently? For example: 'blue jeans', 'white shirt', 'black boots', etc."
            
            state["response_message"] = response_message
            state["follow_up_needed"] = False
                
            return state
            
        except Exception as e:
            state["error_message"] = f"Error in pairing handling: {str(e)}"
            return state
    
    def _handle_vacation(self, state: FashionState) -> FashionState:
        """Handle vacation mode using your existing logic"""
        try:
            # Since we already checked gender in routing, we should have it
            # Get vacation recommendations using your existing service (returns both dialogue and products)
            dialogue, products = self.vacation_service.get_vacation_recommendation(
                state["user_input"], 
                state["conversation_history"]
            )
            state["recommendations"] = products
            state["response_message"] = dialogue  # Use the dialogue returned by the service
            state["follow_up_needed"] = False
                
            return state
            
        except Exception as e:
            state["error_message"] = f"Error in vacation handling: {str(e)}"
            return state
    
    def _handle_general(self, state: FashionState) -> FashionState:
        """Handle general mode using your existing logic"""
        try:
            # Get both response message and products from general service
            general_message, prods = self.general_service.respond(
                state["conversation_history"], 
                state["user_input"]
            )
            state["recommendations"] = prods or []
            state["response_message"] = general_message  # Use the message returned by the service
            state["follow_up_needed"] = False
            return state
            
        except Exception as e:
            state["error_message"] = f"Error in general handling: {str(e)}"
            return state
    
    def _generate_followup(self, state: FashionState) -> FashionState:
        """Generate follow-up question"""
        # Check if this is specifically for gender
        if not state.get("gender"):
            state["follow_up_needed"] = True
            state["follow_up_message"] = "Could you tell me whether this is for men or women?"
            state["response_message"] = "Could you tell me whether this is for men or women?"
            state["is_gender_loop"] = True  # Mark that we're asking for gender
        else:
            # Use the follow-up message set by service handlers
            state["response_message"] = state.get("follow_up_message", "Could you provide more information?")
            state["is_gender_loop"] = False
        
        return state
    
    def _prepare_response(self, state: FashionState) -> FashionState:
        """Prepare WebSocket response messages"""
        messages = []
        messages.append({
                "type": "bot_message",
                "message": state["conversation_history"],
                "message_type": "recommendation_intro"
            })
        if state.get("error_message"):
            messages.append({
                "type": "error",
                "message": state["error_message"]
            })
        elif state.get("follow_up_needed"):
            messages.append({
                "type": "bot_message",
                "message": state.get("follow_up_message", "Could you provide more information?"),
                "message_type": "followup_question"
            })
        elif state.get("is_gender_loop", False):
            # FIXED: Handle gender question specifically
            messages.append({
                "type": "bot_message",
                "message": state.get("response_message", "Could you please tell me your gender?"),
                "message_type": "gender_question"
            })
        else:
            # Use the response message generated by the service handlers
            response_message = state.get("response_message", "Here are some recommendations for you!")
            messages.append({
                "type": "bot_message",
                "message": response_message,
                "message_type": "recommendation_intro"
            })
            
            # Add recommendations if available
            if state.get("recommendations"):
                messages.append({
                    "type": "recommendations",
                    "recommendations": [
                        {
                            "id": i + 1,
                            "product_id": rec['product_id'],
                            "title": rec['title'],
                            "brand_name": rec['brand_name'],
                            "price": rec.get('price', 'N/A'),
                        }
                        for i, rec in enumerate(state["recommendations"][:7])
                    ]
                })
        
        state["websocket_messages"] = messages
        return state

    
    def _check_gender_available(self, state: FashionState) -> str:
        """Check if gender is available in the state"""
        gender = state.get("gender")
        print(gender)
        if gender and gender.lower() in ['male', 'female', 'unisex']:
            return "gender_found"
        else:

            return "gender_missing"
    
    def _decide_service_route(self, state: FashionState) -> str:
        """Decide which service to route to"""
        return state.get("service_mode", "general")
    
    def _check_followup_needed(self, state: FashionState) -> str:
        """Check if follow-up is needed"""
        return "followup" if state.get("follow_up_needed", False) else "complete"
    
    # Helper methods (implement using your existing logic)
    
    def _infer_gender(self, user_input: str, conversation_history: str, gender) -> Optional[str]:
        """Use your existing gender inference logic"""
        return self.gender_service.getGender(conversation_history, user_input, gender)
    
    
    def _generate_occasion_recommendations(self, state: FashionState) -> List[Dict]:
        """Generate occasion recommendations using your existing logic"""
        try:
            parameters = state["current_parameters"]
            parameters_flat = self.occasion_service.get_all_tags_flat(parameters)
            all_tags = parameters_flat["core_tags"] + parameters_flat["inferred_tags"]
            
            gender = state["gender"]
            categories = parameters['product_categories']
            
            recommendations = self.recommendation_service.get_recommendations(
                user_query=state["user_input"], 
                tags=all_tags, 
                gender=[gender] if gender else None,
                sub_categories=categories,
                conversation_history=state["conversation_history"]
            )

            dialogue = self.occasion_service.generate_insightful_statement(state["user_input"], state["conversation_history"], recommendations, parameters)
            
            return dialogue, recommendations
            
        except Exception as e:
            print(f"Error generating occasion recommendations: {e}")
            return []
    
    def _generate_response_message(self, state: FashionState) -> str:
        """Generate appropriate response message - kept for backward compatibility"""
        # This method is now optional since response messages are handled in service handlers
        service_mode = state.get("service_mode")
        recommendations = state.get("recommendations", [])
        
        # Fallback messages if services don't provide response messages
        if service_mode == "occasion":
            return f"Great! I found {len(recommendations)} perfect options for you!"
        elif service_mode == "pairing":
            return f"Perfect! Here are some great pieces that would complement your item beautifully."
        elif service_mode == "vacation":
            return f"Wonderful! Here are some perfect pieces for your vacation destination."
        else:
            return f"Here are some recommendations for you!"

    def _process_bot_response(self, state : FashionState):
        context = self.conversation_service.endTurn(state['response_message'], state['gender'], state['recommendations'])
        state['conversation_history'] = context
        return state

class ChatSession:
    def __init__(self, services_dict):
        self.conversation_history = ""
        self.service_mode = None
        self.current_parameters = None
        self.current_recommendations = None
        self.gender = None
        
        # Initialize LangGraph workflow
        self.fashion_workflow = FashionWorkflow(services_dict)
    
    async def process_with_langgraph(self, user_input: str, client_id: str) -> List[Dict]:
        """Process user input using LangGraph workflow"""
        
        # Create initial state
        initial_state = FashionState(
            user_input=user_input,
            client_id=client_id,
            conversation_history=self.conversation_history,
            service_mode=self.service_mode,
            gender=self.gender,
            current_parameters=self.current_parameters,
            recommendations=[],
            response_message=None,  # Initialize response_message
            websocket_messages=[],
            follow_up_needed=False,
            follow_up_message=None,
            confidence_score=None,
            error_message=None,
            is_gender_loop=False  # Initialize gender loop tracker
        )
        
        try:
            # Run the workflow
            final_state = await self.fashion_workflow.app.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": client_id}}
            )
            
            # Update session state
            self.conversation_history = final_state.get("conversation_history", "")
            self.service_mode = final_state.get("service_mode")
            self.gender = final_state.get("gender")
            self.current_parameters = final_state.get("current_parameters")
            self.current_recommendations = final_state.get("recommendations", [])
            
            # Return messages to send via WebSocket
            return final_state.get("websocket_messages", [])
            
        except Exception as e:
            print(f"Error in LangGraph workflow: {e}")
            return [{
                "type": "error",
                "message": f"Sorry, I encountered an error: {str(e)}"
            }]
