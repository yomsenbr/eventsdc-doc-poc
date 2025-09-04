import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from search_engine import SearchEngine

logger = logging.getLogger(__name__)

class ChatBot:
    """Chatbot for Q&A with document context"""
    
    def __init__(self):
        self.search_engine = SearchEngine()
        self.conversation_history = []
        self.max_context_length = 4000  # Token limit for context
        
        # Initialize with simple rule-based responses
        # In production, this would use a proper LLM like OpenAI GPT or similar
        self.use_llm = False
        
        # Try to initialize OpenAI client if API key is available
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM client if available"""
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                self.use_llm = True
                logger.info("OpenAI client initialized successfully")
            else:
                logger.info("No OpenAI API key found, using rule-based responses")
        except ImportError:
            logger.info("OpenAI library not available, using rule-based responses")
        except Exception as e:
            logger.warning(f"Error initializing OpenAI client: {str(e)}")
    
    def ask_question(self, question: str, context_limit: int = 5) -> Dict[str, Any]:
        """Ask a question and get an answer with document context"""
        try:
            # Search for relevant documents
            search_results = self.search_engine.search(
                query=question,
                search_type="hybrid",
                limit=context_limit
            )
            
            # Prepare context from search results
            context = self._prepare_context(search_results)
            
            # Generate answer
            if self.use_llm:
                answer = self._generate_llm_answer(question, context, search_results)
            else:
                answer = self._generate_rule_based_answer(question, context, search_results)
            
            # Store in conversation history
            conversation_entry = {
                'timestamp': datetime.now().isoformat(),
                'question': question,
                'answer': answer,
                'sources': [
                    {
                        'filename': result['filename'],
                        'score': result['score'],
                        'snippet': result['snippet'][:200] + "..." if len(result['snippet']) > 200 else result['snippet']
                    }
                    for result in search_results
                ]
            }
            
            self.conversation_history.append(conversation_entry)
            
            # Keep only last 10 conversations
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            return {
                'answer': answer,
                'sources': conversation_entry['sources'],
                'context_used': len(search_results) > 0
            }
            
        except Exception as e:
            logger.error(f"Error in chatbot question answering: {str(e)}")
            return {
                'answer': f"I apologize, but I encountered an error while processing your question: {str(e)}",
                'sources': [],
                'context_used': False
            }
    
    def _prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Prepare context string from search results"""
        if not search_results:
            return ""
        
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(search_results):
            snippet = result['snippet']
            filename = result['filename']
            
            context_part = f"Document: {filename}\nContent: {snippet}\n"
            
            # Check if adding this part would exceed context limit
            if total_length + len(context_part) > self.max_context_length:
                break
            
            context_parts.append(context_part)
            total_length += len(context_part)
        
        return "\n---\n".join(context_parts)
    
    def _generate_llm_answer(self, question: str, context: str, search_results: List[Dict[str, Any]]) -> str:
        """Generate answer using LLM"""
        try:
            system_prompt = """You are a helpful assistant that answers questions based on provided document context. 
            Use the document context to provide accurate, relevant answers. If the context doesn't contain enough 
            information to answer the question, say so clearly. Always cite which documents you're referencing."""
            
            user_prompt = f"""Question: {question}
            
Context from documents:
{context}

Please provide a helpful answer based on the context above."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating LLM answer: {str(e)}")
            return self._generate_rule_based_answer(question, context, search_results)
    
    def _generate_rule_based_answer(self, question: str, context: str, search_results: List[Dict[str, Any]]) -> str:
        """Generate rule-based answer when LLM is not available"""
        if not search_results:
            return self._generate_no_context_answer(question)
        
        # Analyze question type
        question_lower = question.lower()
        question_words = question_lower.split()
        
        # Check for question type indicators
        is_what_question = any(word in question_words for word in ['what', 'define', 'definition'])
        is_how_question = any(word in question_words for word in ['how', 'process', 'procedure'])
        is_why_question = any(word in question_words for word in ['why', 'reason', 'because'])
        is_when_question = any(word in question_words for word in ['when', 'date', 'time'])
        is_where_question = any(word in question_words for word in ['where', 'location', 'place'])
        is_who_question = any(word in question_words for word in ['who', 'person', 'people'])
        
        # Generate appropriate response based on search results
        best_result = search_results[0]
        filename = best_result['filename']
        snippet = best_result['snippet']
        
        # Create a contextual answer
        answer_parts = []
        
        if is_what_question:
            answer_parts.append(f"Based on the document '{filename}', here's what I found:")
        elif is_how_question:
            answer_parts.append(f"According to '{filename}', here's information about the process:")
        elif is_why_question:
            answer_parts.append(f"From '{filename}', here's relevant information about the reasons:")
        elif is_when_question:
            answer_parts.append(f"The document '{filename}' contains this temporal information:")
        elif is_where_question:
            answer_parts.append(f"Regarding location, '{filename}' mentions:")
        elif is_who_question:
            answer_parts.append(f"About people or entities, '{filename}' indicates:")
        else:
            answer_parts.append(f"Based on '{filename}', I found this relevant information:")
        
        # Add the most relevant snippet
        answer_parts.append(f"\n{snippet}")
        
        # Add information about additional sources if available
        if len(search_results) > 1:
            additional_sources = [r['filename'] for r in search_results[1:3]]
            answer_parts.append(f"\nAdditional relevant information was found in: {', '.join(additional_sources)}")
        
        # Add disclaimer
        answer_parts.append(f"\n\nThis information is based on a search through {len(search_results)} relevant document(s). For complete details, please refer to the original documents.")
        
        return "".join(answer_parts)
    
    def _generate_no_context_answer(self, question: str) -> str:
        """Generate answer when no relevant documents are found"""
        return f"""I couldn't find relevant information in the indexed documents to answer your question: "{question}"

This could mean:
1. The information might not be available in the current document collection
2. The question might need to be phrased differently for better search results
3. The relevant documents might not be indexed yet

Please try rephrasing your question or check if the relevant documents have been uploaded to the system."""
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_suggested_questions(self, limit: int = 5) -> List[str]:
        """Get suggested questions based on indexed documents"""
        try:
            # Get some sample documents
            stats = self.search_engine.get_stats()
            
            if stats['total_documents'] == 0:
                return [
                    "What documents are available in the system?",
                    "How do I upload a document?",
                    "What file types are supported?"
                ]
            
            # Generate generic questions that work with most document types
            suggestions = [
                "What is the main topic of the uploaded documents?",
                "Can you summarize the key points from the documents?",
                "What are the most important details mentioned?",
                "Are there any specific procedures or processes described?",
                "What dates or timeframes are mentioned in the documents?",
                "Who are the key people or organizations mentioned?",
                "What are the main recommendations or conclusions?",
                "Are there any requirements or guidelines specified?",
                "What contact information is provided?",
                "Are there any deadlines or important dates mentioned?"
            ]
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error generating suggested questions: {str(e)}")
            return ["What can you tell me about the documents?"]
    
    def health_check(self):
        """Check if chatbot is healthy"""
        try:
            # Test search engine
            self.search_engine.health_check()
            
            # Test basic functionality
            test_response = self.ask_question("test question")
            if not test_response.get('answer'):
                raise Exception("Failed to generate test answer")
                
        except Exception as e:
            raise Exception(f"Chatbot health check failed: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chatbot statistics"""
        search_stats = self.search_engine.get_stats()
        
        return {
            'total_conversations': len(self.conversation_history),
            'llm_enabled': self.use_llm,
            'search_engine_stats': search_stats
        }