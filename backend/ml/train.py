import sys
import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, multilabel_confusion_matrix 
import logging

import numpy as np
import tensorflow as tf
from keras.callbacks import EarlyStopping
from keras.models import Sequential
from keras.layers import Embedding, GlobalMaxPooling1D, Dense



project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
sys.path.insert(0, project_root)

from backend.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for the Neural Network
MAX_WORDS = 10000 
MAX_LEN = 300 
EMBEDDING_DIM = 100 


CATEGORIES = [
    'public_resource', 'public_events', 'vocational_training',
    'education_outreach', 'access_policy'
]


def train_classification_model():
    """
    Train the multi-label Neural Network classification model.
    """
    try:
        logger.info("Training Neural Network classification model...")
        
        # --- 1. DATA LOADING AND CUSTOM MULTI-LABEL PARSING ---
        data_path = os.path.join(project_root, 'training_data/classification_training_data.csv')
            
        if not os.path.exists(data_path):
            logger.error(f"Training data not found at: {data_path}")
            return None, None
            
        with open(data_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        data = []
        for line in lines[1:]:
            line = line.strip()
            if line and '|' in line:
                try:
                    parts = line.split('|', 1)
                    labels_str = parts[0].strip()
                    text = parts[1].strip().strip('"') 
                    
                    # Identify which classes are active
                    active_classes = {c.strip() for c in labels_str.split(',') if c.strip()}
                    
                    # Create the one-hot-encoded row
                    row = [text]
                    for category in CATEGORIES:
                        row.append(1 if category in active_classes else 0)
                    
                    data.append(row)
                except Exception as e:
                    logger.warning(f"Skipping malformed line: {line[:50]}... Error: {e}")
                    continue

        df = pd.DataFrame(data, columns=['text'] + CATEGORIES)
        logger.info(f"Total training samples loaded: {len(df)}")
        
        # --- 2. SHUFFLE THE DATASET ---
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)
        logger.info("Data shuffled successfully.")

        # Split features and labels
        X = df['text']
        Y = df[CATEGORIES].values

        # --- 3. TOKENIZATION AND PADDING ---
        tokenizer = tf.keras.preprocessing.text.Tokenizer(num_words=MAX_WORDS)
        tokenizer.fit_on_texts(X)
        sequences = tokenizer.texts_to_sequences(X)
        padded_sequences = tf.keras.preprocessing.sequence.pad_sequences(sequences, maxlen=MAX_LEN)
        
        vocab_size = len(tokenizer.word_index) + 1

        # --- 4. SPLIT DATASETS (70% Train, 15% Validation, 15% Test) ---
        X_train, X_temp, Y_train, Y_temp = train_test_split(
            padded_sequences, 
            Y, 
            test_size=0.3,
            random_state=42,
            shuffle=True
        )

        # dataset split
        X_val, X_test, Y_val, Y_test = train_test_split(
            X_temp, 
            Y_temp, 
            test_size=0.5,
            random_state=42,
            shuffle=True
        )
        
        logger.info(f"Train/Val/Test Split: {len(X_train)} / {len(X_val)} / {len(X_test)} samples.")

        # --- 5. MODEL DEFINITION AND TRAINING ---
        model = Sequential([
            Embedding(vocab_size, EMBEDDING_DIM, input_length=MAX_LEN),
            GlobalMaxPooling1D(),
            Dense(128, activation='relu'),
            # Output layer: number of classes, SIGMOID is CRITICAL for multi-label
            Dense(len(CATEGORIES), activation='sigmoid') 
        ])

        model.compile(
            optimizer='adam',
            # BINARY_CROSSENTROPY is CRITICAL for multi-label classification
            loss='binary_crossentropy', 
            metrics=['accuracy', tf.keras.metrics.Precision(), tf.keras.metrics.Recall()]
        )

        early_stopping = EarlyStopping(
            monitor='val_loss', 
            patience=5, 
            restore_best_weights=True
        )

        logger.info(f"Starting training on {len(X_train)} samples...")
        model.fit(
            X_train, Y_train,
            epochs=20,
            batch_size=32,
            validation_data=(X_val, Y_val),
            callbacks=[early_stopping],
            verbose=1
        )


        # --- 6. EVALUATION ---
        logger.info("\nEvaluating on Test Set...")
        # Unpack all four returned values
        loss, acc, prec, recall = model.evaluate(X_test, Y_test, verbose=0) 

        # Calculate Error Rate
        error_rate = 1.0 - acc 

        logger.info(f"Test Loss: {loss:.4f}, Test Accuracy: {acc:.4f}")
        # Log the calculated error rate
        logger.info(f"Test Error Rate: {error_rate * 100:.2f}%") 
        logger.info(f"Test Precision: {prec:.4f}, Test Recall: {recall:.4f}")

        # Generate predictions and classification report
        y_pred_proba = model.predict(X_test)
        
        y_pred = (y_pred_proba > Config.CLASSIFICATION_THRESHOLD).astype(int) 

        report = classification_report(Y_test, y_pred, target_names=CATEGORIES, zero_division=0)
        logger.info("Classification Report:\n" + report + "\n")
        
        mcm = multilabel_confusion_matrix(Y_test, y_pred)        
        model_save_dir = os.path.join(project_root, Config.MODEL_PATH)
        os.makedirs(model_save_dir, exist_ok=True)
        

        # --- 7. SAVE MODEL AND TOKENIZER ---
        model.save(os.path.join(model_save_dir, "classification_nn_model.keras")) 
        joblib.dump(tokenizer, os.path.join(model_save_dir, "classification_tokenizer.pkl")) 

        logger.info("NN Classification model trained and saved successfully")
        
        return model, tokenizer

    except Exception as e:
        logger.error(f"Error training NN classification model: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None


if __name__ == "__main__":
    logger.info("Starting model training (Classification Only)...")
    
    # Train classification model
    classification_model, classification_tokenizer = train_classification_model()
    
    if classification_model:
        logger.info("Classification training pipeline finished.")
    else:
        logger.error("Classification training failed.")
