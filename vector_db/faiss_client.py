"""
FAISS-based vector database client as alternative to ChromaDB.
FAISS is fully Python-based and works with PyInstaller.
"""
import os
import sys
import json
import pickle
import numpy as np

# Lazy import logger
def get_logger():
    """Get logger instance (lazy import)."""
    try:
        from core.logger import logger
        return logger
    except ImportError:
        import logging
        return logging.getLogger("local_brain")

# Lazy import FAISS and sentence transformers
_faiss = None
_sentence_transformer = None
_model = None

def _import_faiss():
    """Lazy import FAISS."""
    global _faiss
    if _faiss is None:
        try:
            import faiss
            _faiss = faiss
        except ImportError:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu")
    return _faiss

def _import_sentence_transformer():
    """Lazy import sentence transformers."""
    global _sentence_transformer, _model
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformer = SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers not available. Install with: pip install sentence-transformers")
    
    # Initialize model if not already done
    if _model is None:
        try:
            # Use a lightweight multilingual model
            _model = _sentence_transformer('paraphrase-multilingual-MiniLM-L12-v2')
        except Exception as e:
            # Fallback to English-only model
            try:
                _model = _sentence_transformer('all-MiniLM-L6-v2')
            except Exception as e2:
                raise ImportError(f"Could not load sentence transformer model: {e2}")
    
    return _model

def get_base_dir():
    """Get base directory for data storage."""
    if hasattr(sys, '_MEIPASS'):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if 'vector_db' in base_dir:
                base_dir = os.path.dirname(base_dir)
            return base_dir
    else:
        return os.getcwd()

class FAISSVectorDB:
    """FAISS-based vector database implementation."""
    
    def __init__(self, storage_dir=None):
        """Initialize FAISS vector database."""
        self.logger = get_logger()
        
        if storage_dir is None:
            storage_dir = os.path.join(get_base_dir(), "vector_db_storage")
        
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # File paths
        self.index_file = os.path.join(self.storage_dir, "faiss.index")
        self.metadata_file = os.path.join(self.storage_dir, "metadata.json")
        self.documents_file = os.path.join(self.storage_dir, "documents.pkl")
        
        # Initialize FAISS and model
        try:
            self.faiss = _import_faiss()
            self.model = _import_sentence_transformer()
            self.dimension = self.model.get_sentence_embedding_dimension()
            
            # Load or create index
            self.index = None
            self.metadata = {}  # {id: metadata_dict}
            self.documents = {}  # {id: document_text}
            self.id_to_index = {}  # {id: index_in_faiss}
            self.index_to_id = {}  # {index_in_faiss: id}
            
            self._load_index()
            
            self.logger.info(f"FAISS vector database initialized at {self.storage_dir}")
        except Exception as e:
            self.logger.error(f"Failed to initialize FAISS: {e}", exc_info=True)
            raise
    
    def _load_index(self):
        """Load existing index and metadata."""
        try:
            # Load FAISS index
            if os.path.exists(self.index_file):
                self.index = self.faiss.read_index(self.index_file)
                self.logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            else:
                # Create new index (L2 distance)
                self.index = self.faiss.IndexFlatL2(self.dimension)
                self.logger.info("Created new FAISS index")
            
            # Load metadata
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata_data = json.load(f)
                    # Convert from list format back to dict
                    if isinstance(metadata_data, list):
                        self.metadata = {item["id"]: item["metadata"] for item in metadata_data}
                    else:
                        # Legacy format (dict)
                        self.metadata = metadata_data
            
            # Load documents
            if os.path.exists(self.documents_file):
                with open(self.documents_file, 'rb') as f:
                    self.documents = pickle.load(f)
            
            # Rebuild id_to_index mapping
            # The order in metadata should match the order in FAISS index
            # We need to ensure consistency
            if self.index.ntotal > 0:
                # If we have an index with vectors, metadata and documents should match
                if len(self.metadata) != self.index.ntotal:
                    self.logger.warning(f"Mismatch: index has {self.index.ntotal} vectors but metadata has {len(self.metadata)} entries. Rebuilding...")
                    # Rebuild: clear and start fresh
                    self.index = self.faiss.IndexFlatL2(self.dimension)
                    self.metadata = {}
                    self.documents = {}
                    self.id_to_index = {}
                    self.index_to_id = {}
                else:
                    # Rebuild mappings - order matters!
                    for idx, (chat_id, _) in enumerate(self.metadata.items()):
                        self.id_to_index[chat_id] = idx
                        self.index_to_id[idx] = chat_id
            
            self.logger.debug(f"Loaded {len(self.metadata)} entries from FAISS database")
        except Exception as e:
            self.logger.error(f"Failed to load FAISS index: {e}", exc_info=True)
            # Create new index on error
            self.index = self.faiss.IndexFlatL2(self.dimension)
            self.metadata = {}
            self.documents = {}
            self.id_to_index = {}
            self.index_to_id = {}
    
    def _save_index(self):
        """Save index and metadata to disk."""
        try:
            # Save FAISS index
            if self.index.ntotal > 0:
                self.faiss.write_index(self.index, self.index_file)
            
            # Save metadata - preserve order by using list of tuples
            # Convert to list format to preserve insertion order
            metadata_list = []
            for idx in range(len(self.id_to_index)):
                chat_id = self.index_to_id.get(idx)
                if chat_id and chat_id in self.metadata:
                    metadata_list.append({
                        "id": chat_id,
                        "metadata": self.metadata[chat_id]
                    })
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_list, f, ensure_ascii=False, indent=2)
            
            # Save documents
            with open(self.documents_file, 'wb') as f:
                pickle.dump(self.documents, f)
            
            self.logger.debug(f"Saved FAISS index ({self.index.ntotal} vectors) and metadata ({len(metadata_list)} entries)")
        except Exception as e:
            self.logger.error(f"Failed to save FAISS index: {e}", exc_info=True)
    
    def add(self, ids, documents, metadatas):
        """Add documents to the index."""
        try:
            # Generate embeddings
            embeddings = self.model.encode(documents, show_progress_bar=False)
            embeddings = np.array(embeddings).astype('float32')
            
            # Add to index
            self.index.add(embeddings)
            
            # Update mappings
            start_idx = len(self.id_to_index)
            for i, chat_id in enumerate(ids):
                idx = start_idx + i
                self.id_to_index[str(chat_id)] = idx
                self.index_to_id[idx] = str(chat_id)
                self.metadata[str(chat_id)] = metadatas[i] if i < len(metadatas) else {}
                self.documents[str(chat_id)] = documents[i] if i < len(documents) else ""
            
            # Save to disk
            self._save_index()
            
            self.logger.debug(f"Added {len(ids)} documents to FAISS index")
        except Exception as e:
            self.logger.error(f"Failed to add documents to FAISS: {e}", exc_info=True)
            raise
    
    def update(self, ids, documents, metadatas):
        """Update documents in the index."""
        try:
            # For update, we need to remove old entries and add new ones
            # FAISS doesn't support direct updates, so we rebuild
            ids_to_update = [str(id) for id in ids]
            
            # Remove old entries (collect indices to remove)
            indices_to_remove = []
            for chat_id in ids_to_update:
                if chat_id in self.id_to_index:
                    idx = self.id_to_index[chat_id]
                    indices_to_remove.append(idx)
            
            if indices_to_remove:
                # Remove from metadata and documents before rebuild
                for chat_id in ids_to_update:
                    if chat_id in self.metadata:
                        del self.metadata[chat_id]
                    if chat_id in self.documents:
                        del self.documents[chat_id]
                
                # Rebuild index without removed entries
                self._rebuild_index_excluding(indices_to_remove)
            
            # Add updated entries
            self.add(ids, documents, metadatas)
            
            self.logger.debug(f"Updated {len(ids)} documents in FAISS index")
        except Exception as e:
            self.logger.error(f"Failed to update documents in FAISS: {e}", exc_info=True)
            raise
    
    def _rebuild_index_excluding(self, indices_to_exclude):
        """Rebuild index excluding specified indices."""
        try:
            # Get all documents that should remain (by chat_id, not by index)
            exclude_set = set(indices_to_exclude)
            all_ids = []
            all_metadatas = []
            all_documents = []
            
            # Collect all chat_ids that should remain
            for chat_id in list(self.metadata.keys()):
                if chat_id in self.id_to_index:
                    idx = self.id_to_index[chat_id]
                    if idx not in exclude_set:
                        all_ids.append(chat_id)
                        all_metadatas.append(self.metadata.get(chat_id, {}))
                        all_documents.append(self.documents.get(chat_id, ""))
            
            # Rebuild index from scratch
            self.index = self.faiss.IndexFlatL2(self.dimension)
            self.id_to_index = {}
            self.index_to_id = {}
            
            if all_documents:
                # Regenerate embeddings for remaining documents
                embeddings = self.model.encode(all_documents, show_progress_bar=False)
                embeddings = np.array(embeddings).astype('float32')
                self.index.add(embeddings)
                
                # Rebuild mappings
                for i, chat_id in enumerate(all_ids):
                    self.id_to_index[chat_id] = i
                    self.index_to_id[i] = chat_id
            
            self.logger.debug(f"Rebuilt FAISS index with {len(all_ids)} entries")
        except Exception as e:
            self.logger.error(f"Failed to rebuild FAISS index: {e}", exc_info=True)
            raise
    
    def delete(self, ids):
        """Delete documents from the index."""
        try:
            ids_to_delete = [str(id) for id in ids]
            indices_to_remove = []
            
            for chat_id in ids_to_delete:
                if chat_id in self.id_to_index:
                    idx = self.id_to_index[chat_id]
                    indices_to_remove.append(idx)
                    del self.metadata[chat_id]
                    del self.documents[chat_id]
            
            if indices_to_remove:
                self._rebuild_index_excluding(indices_to_remove)
                self._save_index()
            
            self.logger.debug(f"Deleted {len(ids_to_delete)} documents from FAISS index")
        except Exception as e:
            self.logger.error(f"Failed to delete documents from FAISS: {e}", exc_info=True)
            raise
    
    def query(self, query_texts, n_results=3, where=None):
        """
        Search for similar documents.
        
        Args:
            query_texts: List of query strings
            n_results: Number of results to return
            where: Dictionary of metadata filters (e.g., {"chat_id": "123"})
        """
        try:
            if self.index.ntotal == 0:
                return {
                    "ids": [[]],
                    "distances": [[]],
                    "documents": [[]],
                    "metadatas": [[]]
                }
            
            # Generate query embedding
            query_embeddings = self.model.encode(query_texts, show_progress_bar=False)
            query_embeddings = np.array(query_embeddings).astype('float32')
            
            # Search more results if filtering is needed (to compensate for filtered results)
            search_limit = n_results * 3 if where else n_results
            distances, indices = self.index.search(query_embeddings, min(search_limit, self.index.ntotal))
            
            # Format results
            results = {
                "ids": [],
                "distances": [],
                "documents": [],
                "metadatas": []
            }
            
            for query_idx in range(len(query_texts)):
                result_ids = []
                result_distances = []
                result_documents = []
                result_metadatas = []
                
                for i, idx in enumerate(indices[query_idx]):
                    if idx >= 0 and idx in self.index_to_id:
                        doc_id = self.index_to_id[idx]
                        metadata = self.metadata.get(doc_id, {})
                        
                        # Apply metadata filters if provided
                        if where:
                            match = True
                            for key, value in where.items():
                                if metadata.get(key) != value:
                                    match = False
                                    break
                            if not match:
                                continue
                        
                        result_ids.append(doc_id)
                        result_distances.append(float(distances[query_idx][i]))
                        result_documents.append(self.documents.get(doc_id, ""))
                        result_metadatas.append(metadata)
                        
                        # Stop when we have enough results
                        if len(result_ids) >= n_results:
                            break
                
                results["ids"].append(result_ids)
                results["distances"].append(result_distances)
                results["documents"].append(result_documents)
                results["metadatas"].append(result_metadatas)
            
            return results
        except Exception as e:
            self.logger.error(f"Failed to query FAISS index: {e}", exc_info=True)
            return {
                "ids": [[]],
                "distances": [[]],
                "documents": [[]],
                "metadatas": [[]]
            }
    
    def get(self, ids=None):
        """Get documents by IDs."""
        try:
            if ids is None:
                # Return all
                all_ids = list(self.metadata.keys())
                all_documents = [self.documents.get(id, "") for id in all_ids]
                all_metadatas = [self.metadata.get(id, {}) for id in all_ids]
                return {
                    "ids": all_ids,
                    "documents": all_documents,
                    "metadatas": all_metadatas
                }
            else:
                # Return specific IDs
                result_ids = []
                result_documents = []
                result_metadatas = []
                
                for id in ids:
                    id_str = str(id)
                    if id_str in self.metadata:
                        result_ids.append(id_str)
                        result_documents.append(self.documents.get(id_str, ""))
                        result_metadatas.append(self.metadata.get(id_str, {}))
                
                return {
                    "ids": result_ids,
                    "documents": result_documents,
                    "metadatas": result_metadatas
                }
        except Exception as e:
            self.logger.error(f"Failed to get documents from FAISS: {e}", exc_info=True)
            return {
                "ids": [],
                "documents": [],
                "metadatas": []
            }

