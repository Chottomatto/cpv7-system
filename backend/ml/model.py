import pandas as pd
import numpy as np
import tensorflow as tf
import joblib
import logging
from backend.config import Config
from typing import Dict, Any, Union 

logger = logging.getLogger(__name__)

# --- ArticleClassifier Class (Classification Only) ---

class ArticleClassifier:
    def __init__(self):
        self.nn_model = None 
        self.tokenizer = None 
        
        # Must match MAX_LEN from train.py
        self.max_len = 300 
        self.categories = [
            'ethical_sourcing_policy', 'policy_waste_disposal_hazardous_materials', 'policy_waste_disposal_landfill_policy',
            'policy_for_minimisation_of_plastic_use', 'policy_for_minimisation_of_disposable_items', 'disposable_policy', 'minimisation_policies_extended_to_suppliers'
        ]
        

    def load_models(self):
        """Load trained models (NN classification and tokenizer) from disk."""
        try:
            # Load Keras classification model
            self.nn_model = tf.keras.models.load_model(f"{Config.MODEL_PATH}/classification_nn_model.keras")
            logger.info("Keras Classification model loaded successfully")
        except Exception as e:
            logger.warning(f"Keras Classification model not found: {e}")
            
        try:
            # Load the tokenizer
            self.tokenizer = joblib.load(f"{Config.MODEL_PATH}/classification_tokenizer.pkl")
            logger.info("Keras Tokenizer loaded successfully")
        except Exception as e:
            logger.warning(f"Keras Tokenizer not found: {e}")
            
        if not self.nn_model or not self.tokenizer:
            logger.error("One or more ML models failed to load. Classification processing will be disabled.")

    def contains_guimaras_keywords(self, text: str) -> bool:
        """Check if text contains Guimaras-related keywords"""
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in Config.GUIMARAS_KEYWORDS)

    def classify_article(self, text: str) -> Dict[str, float]:
        """
        Classify article into categories using the NN model.
        """
        if not self.nn_model or not self.tokenizer or not text:
            return {cat: 0.0 for cat in self.categories}
        
        try:
            sequences = self.tokenizer.texts_to_sequences([text])
            
            padded_sequence = tf.keras.preprocessing.sequence.pad_sequences(
                sequences, 
                maxlen=self.max_len, 
                padding='post', 
                truncating='post'
            )
            
            probabilities = self.nn_model.predict(padded_sequence)[0]
            
            results = {}
            for i, category in enumerate(self.categories):
                results[category] = float(probabilities[i])
            return results
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return {cat: 0.0 for cat in self.categories}

    def calculate_metrics_score(self, article_data: Dict[str, Any]) -> float:
        """Calculate the final composite relevance score for the article."""
        total_score = 0.0
        
        # Score component 1: DOI presence
        if article_data.get('doi'):
            total_score += 0.27
            
        # Score component 2: Category relevance (from classification)
        category_scores = article_data.get('categories', {})
        for category, score in category_scores.items():
            if score > Config.CLASSIFICATION_THRESHOLD:
                # Use category score multiplied by its predefined weight
                weight = Config.CATEGORY_WEIGHTS.get(category, 0)
                total_score += score * weight
                
        
        # Ensure score is capped at 1.0
        return min(total_score, 1.0)

    def process_article(self, article_data: Dict[str, Any]) -> Union[Dict[str, Any], None]:
        """Process a single article through the ML pipeline"""
        try:
            content = article_data.get('content', '')
            title = article_data.get('title', '')
            
            # Combine title and content for analysis (RAW TEXT)
            full_text = f"{title} {content}".strip()
            
            if not full_text or len(full_text) < 50:
                return None
            
            # STEP 1: Filter check (checks for guimaras keywords)
            if not self.contains_guimaras_keywords(full_text):
                return None
            
            # STEP 2: Classify article
            categories = self.classify_article(full_text)
            
            # STEP 3: Calculate total score
            processed_data = article_data.copy()
            processed_data['categories'] = categories
            processed_data['total_score'] = self.calculate_metrics_score(processed_data)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None