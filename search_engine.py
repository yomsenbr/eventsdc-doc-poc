import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re

logger = logging.getLogger(__name__)

class SearchEngine:
    """Search engine with keyword, vector, and hybrid search capabilities with deduplication"""
    
    def __init__(self):
        self.documents = {}  # Store documents with hash as key
        self.embeddings = {}  # Store document embeddings
        self.inverted_index = {}  # Keyword search index
        self.documents_file = "search_documents.json"
        self.embeddings_file = "document_embeddings.json"
        
        # Initialize sentence transformer for vector search
        try:
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Could not load sentence transformer: {e}")
            self.sentence_model = None
        
        # Load existing data
        self._load_documents()
        self._load_embeddings()
        self._build_inverted_index()
    
    def index_document(self, filename: str, content: str, file_hash: str, content_hash: str) -> str:
        """Index a document with proper deduplication"""
        try:
            # Check for duplicate content hash
            for doc_id, doc in self.documents.items():
                if doc.get('content_hash') == content_hash:
                    logger.info(f"Document with same content already indexed: {doc['filename']}")
                    return doc_id
            
            # Create document entry
            doc_id = file_hash  # Use file hash as document ID
            document = {
                'id': doc_id,
                'filename': filename,
                'content': content,
                'file_hash': file_hash,
                'content_hash': content_hash,
                'indexed_date': datetime.now().isoformat(),
                'content_length': len(content),
                'chunks': self._create_chunks(content)
            }
            
            # Store document
            self.documents[doc_id] = document
            
            # Create embeddings for vector search
            if self.sentence_model:
                self._create_embeddings(doc_id, document['chunks'])
            
            # Update inverted index for keyword search
            self._update_inverted_index(doc_id, content)
            
            # Save data
            self._save_documents()
            self._save_embeddings()
            
            logger.info(f"Successfully indexed document: {filename} (ID: {doc_id})")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error indexing document {filename}: {str(e)}")
            raise
    
    def search(self, query: str, search_type: str = "hybrid", limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents with specified method"""
        try:
            if search_type == "keyword":
                results = self._keyword_search(query, limit)
            elif search_type == "vector":
                results = self._vector_search(query, limit)
            elif search_type == "hybrid":
                results = self._hybrid_search(query, limit)
            else:
                raise ValueError(f"Unknown search type: {search_type}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            raise
    
    def _keyword_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Perform keyword-based search"""
        query_terms = self._tokenize(query.lower())
        doc_scores = {}
        
        for term in query_terms:
            if term in self.inverted_index:
                for doc_id, tf_score in self.inverted_index[term].items():
                    if doc_id in doc_scores:
                        doc_scores[doc_id] += tf_score
                    else:
                        doc_scores[doc_id] = tf_score
        
        # Sort by score and get top results
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        results = []
        for doc_id, score in sorted_docs:
            if doc_id in self.documents:
                doc = self.documents[doc_id]
                snippet = self._get_snippet(doc['content'], query)
                
                results.append({
                    'document_id': doc_id,
                    'filename': doc['filename'],
                    'score': score,
                    'search_type': 'keyword',
                    'snippet': snippet,
                    'content_hash': doc.get('content_hash', ''),
                    'indexed_date': doc.get('indexed_date', '')
                })
        
        return results
    
    def _vector_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Perform vector-based semantic search"""
        if not self.sentence_model or not self.embeddings:
            return []
        
        try:
            # Create query embedding
            query_embedding = self.sentence_model.encode([query])
            
            doc_scores = []
            for doc_id, doc_embeddings in self.embeddings.items():
                if doc_id not in self.documents:
                    continue
                
                # Calculate similarity with all chunks and take the best score
                max_similarity = 0
                best_chunk_idx = 0
                
                for i, chunk_embedding in enumerate(doc_embeddings['chunk_embeddings']):
                    similarity = cosine_similarity(query_embedding, [chunk_embedding])[0][0]
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_chunk_idx = i
                
                doc_scores.append((doc_id, max_similarity, best_chunk_idx))
            
            # Sort by similarity score
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for doc_id, score, chunk_idx in doc_scores[:limit]:
                doc = self.documents[doc_id]
                chunk = doc['chunks'][chunk_idx] if chunk_idx < len(doc['chunks']) else doc['content'][:500]
                
                results.append({
                    'document_id': doc_id,
                    'filename': doc['filename'],
                    'score': float(score),
                    'search_type': 'vector',
                    'snippet': chunk[:500] + "..." if len(chunk) > 500 else chunk,
                    'content_hash': doc.get('content_hash', ''),
                    'indexed_date': doc.get('indexed_date', '')
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return []
    
    def _hybrid_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Combine keyword and vector search results"""
        keyword_results = self._keyword_search(query, limit * 2)
        vector_results = self._vector_search(query, limit * 2)
        
        # Combine and normalize scores
        combined_scores = {}
        
        # Add keyword scores (normalized)
        if keyword_results:
            max_keyword_score = max(r['score'] for r in keyword_results)
            for result in keyword_results:
                doc_id = result['document_id']
                normalized_score = result['score'] / max_keyword_score if max_keyword_score > 0 else 0
                combined_scores[doc_id] = {
                    'keyword_score': normalized_score,
                    'vector_score': 0,
                    'result': result
                }
        
        # Add vector scores (already normalized 0-1)
        for result in vector_results:
            doc_id = result['document_id']
            if doc_id in combined_scores:
                combined_scores[doc_id]['vector_score'] = result['score']
                # Update snippet if vector score is higher
                if result['score'] > combined_scores[doc_id]['keyword_score']:
                    combined_scores[doc_id]['result']['snippet'] = result['snippet']
            else:
                combined_scores[doc_id] = {
                    'keyword_score': 0,
                    'vector_score': result['score'],
                    'result': result
                }
        
        # Calculate hybrid score (weighted combination)
        keyword_weight = 0.4
        vector_weight = 0.6
        
        final_results = []
        for doc_id, scores in combined_scores.items():
            hybrid_score = (scores['keyword_score'] * keyword_weight + 
                           scores['vector_score'] * vector_weight)
            
            result = scores['result'].copy()
            result['score'] = hybrid_score
            result['search_type'] = 'hybrid'
            result['keyword_score'] = scores['keyword_score']
            result['vector_score'] = scores['vector_score']
            
            final_results.append(result)
        
        # Sort by hybrid score and return top results
        final_results.sort(key=lambda x: x['score'], reverse=True)
        return final_results[:limit]
    
    def deduplicate_results(self, results: List[Dict[str, Any]], similarity_threshold: float = 0.9) -> List[Dict[str, Any]]:
        """Remove duplicate results based on content similarity"""
        if not results:
            return results
        
        deduplicated = []
        seen_content_hashes = set()
        
        for result in results:
            content_hash = result.get('content_hash', '')
            
            # Skip if we've seen this exact content
            if content_hash and content_hash in seen_content_hashes:
                logger.info(f"Skipping duplicate result: {result['filename']}")
                continue
            
            # Check for similar content using snippet similarity
            is_duplicate = False
            for existing_result in deduplicated:
                if self._are_snippets_similar(result.get('snippet', ''), 
                                            existing_result.get('snippet', ''), 
                                            similarity_threshold):
                    logger.info(f"Skipping similar result: {result['filename']} (similar to {existing_result['filename']})")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(result)
                if content_hash:
                    seen_content_hashes.add(content_hash)
        
        return deduplicated
    
    def _are_snippets_similar(self, snippet1: str, snippet2: str, threshold: float) -> bool:
        """Check if two snippets are similar using simple text comparison"""
        if not snippet1 or not snippet2:
            return False
        
        # Simple similarity check using common words
        words1 = set(self._tokenize(snippet1.lower()))
        words2 = set(self._tokenize(snippet2.lower()))
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold
    
    def delete_document(self, doc_id: str):
        """Delete a document from the search index"""
        try:
            if doc_id in self.documents:
                # Remove from documents
                deleted_doc = self.documents.pop(doc_id)
                
                # Remove from embeddings
                if doc_id in self.embeddings:
                    del self.embeddings[doc_id]
                
                # Rebuild inverted index (simple approach)
                self._build_inverted_index()
                
                # Save changes
                self._save_documents()
                self._save_embeddings()
                
                logger.info(f"Deleted document: {deleted_doc.get('filename', doc_id)}")
                return True
            else:
                logger.warning(f"Document not found for deletion: {doc_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            raise
    
    def health_check(self):
        """Check if search engine is healthy"""
        if not self.sentence_model:
            raise Exception("Sentence transformer model not loaded")
        
        # Test basic functionality
        test_query = "test"
        try:
            self._keyword_search(test_query, 1)
            if self.embeddings:
                self._vector_search(test_query, 1)
        except Exception as e:
            raise Exception(f"Search functionality test failed: {str(e)}")
    
    def _create_chunks(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split content into chunks for better embedding"""
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                # Find the last sentence ending before the chunk limit
                last_period = content.rfind('.', start, end)
                last_newline = content.rfind('\n', start, end)
                break_point = max(last_period, last_newline)
                
                if break_point > start:
                    end = break_point + 1
            
            chunks.append(content[start:end].strip())
            start = end - overlap
        
        return chunks
    
    def _create_embeddings(self, doc_id: str, chunks: List[str]):
        """Create embeddings for document chunks"""
        try:
            embeddings_list = self.sentence_model.encode(chunks)
            self.embeddings[doc_id] = {
                'chunk_embeddings': embeddings_list.tolist(),
                'created_date': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error creating embeddings for {doc_id}: {str(e)}")
    
    def _update_inverted_index(self, doc_id: str, content: str):
        """Update inverted index with document terms"""
        terms = self._tokenize(content.lower())
        term_freq = {}
        
        # Count term frequencies
        for term in terms:
            if term in term_freq:
                term_freq[term] += 1
            else:
                term_freq[term] = 1
        
        # Update inverted index
        for term, freq in term_freq.items():
            if term not in self.inverted_index:
                self.inverted_index[term] = {}
            
            # Simple TF score (could be enhanced with TF-IDF)
            self.inverted_index[term][doc_id] = freq
    
    def _build_inverted_index(self):
        """Rebuild the inverted index from all documents"""
        self.inverted_index = {}
        for doc_id, doc in self.documents.items():
            self._update_inverted_index(doc_id, doc['content'])
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Remove punctuation and split on whitespace
        cleaned = re.sub(r'[^\w\s]', ' ', text)
        tokens = cleaned.split()
        
        # Filter out very short tokens and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        tokens = [token for token in tokens if len(token) > 2 and token.lower() not in stop_words]
        
        return tokens
    
    def _get_snippet(self, content: str, query: str, snippet_length: int = 300) -> str:
        """Extract relevant snippet from content based on query"""
        query_terms = self._tokenize(query.lower())
        content_lower = content.lower()
        
        # Find the best position for snippet
        best_position = 0
        max_matches = 0
        
        # Check different positions
        for i in range(0, len(content) - snippet_length, 100):
            snippet_text = content[i:i + snippet_length].lower()
            matches = sum(1 for term in query_terms if term in snippet_text)
            
            if matches > max_matches:
                max_matches = matches
                best_position = i
        
        # Extract snippet and clean it up
        snippet = content[best_position:best_position + snippet_length]
        
        # Try to start and end at word boundaries
        if best_position > 0:
            first_space = snippet.find(' ')
            if first_space > 0:
                snippet = snippet[first_space + 1:]
        
        last_space = snippet.rfind(' ')
        if last_space > 0 and last_space < len(snippet) - 1:
            snippet = snippet[:last_space]
        
        return snippet.strip()
    
    def _save_documents(self):
        """Save documents to file"""
        try:
            with open(self.documents_file, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving documents: {str(e)}")
    
    def _load_documents(self):
        """Load documents from file"""
        try:
            if os.path.exists(self.documents_file):
                with open(self.documents_file, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                logger.info(f"Loaded {len(self.documents)} documents from storage")
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
    
    def _save_embeddings(self):
        """Save embeddings to file"""
        try:
            with open(self.embeddings_file, 'w') as f:
                json.dump(self.embeddings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving embeddings: {str(e)}")
    
    def _load_embeddings(self):
        """Load embeddings from file"""
        try:
            if os.path.exists(self.embeddings_file):
                with open(self.embeddings_file, 'r') as f:
                    self.embeddings = json.load(f)
                logger.info(f"Loaded embeddings for {len(self.embeddings)} documents")
        except Exception as e:
            logger.error(f"Error loading embeddings: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics"""
        return {
            'total_documents': len(self.documents),
            'total_terms': len(self.inverted_index),
            'has_vector_search': self.sentence_model is not None,
            'total_embeddings': len(self.embeddings)
        }