import os
import cv2
import numpy as np
from tensorflow import keras
from tensorflow.keras import utils, models
from sklearn.model_selection import train_test_split
from CNNModel import model

# Paths to dataset
DATASET_PATH = "chess_dataset_v1"
CATEGORIES = ["empty", "black_piece", "white_piece"]
IMG_SIZE = 64  # Resize images to 64x64 pixels

# Enhanced preprocessing to detect edges and textures (helps with white on white)
def preprocess_image(img):
    """
    Multi-layer preprocessing to distinguish pieces from empty squares.
    
    Layer 1: Color information (basic classification)
    Layer 2: Texture variance (pieces have more texture than flat squares)
    Layer 3: Edge density in CENTER (pieces create edges, board lines are at boundaries)
    Layer 4: Gradient magnitude (3D pieces have stronger gradients than flat squares)
    """
    img_resized = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
    
    # Layer 1: Original BGR color (normalized)
    bgr = img_resized.astype(np.float32) / 255.0
    
    # Layer 2: Texture variance (pieces have more texture variation)
    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    
    # Layer 3: Edge detection focused on CENTER of square (not boundaries)
    # Reduce sensitivity to avoid picking up board lines
    edges = cv2.Canny(gray, 100, 200).astype(np.float32) / 255.0
    
    # Mask out the outer 20% of the square (where board lines are)
    mask = np.ones_like(edges)
    border = int(IMG_SIZE * 0.15)  # 15% border
    mask[:border, :] = 0  # Top
    mask[-border:, :] = 0  # Bottom
    mask[:, :border] = 0  # Left
    mask[:, -border:] = 0  # Right
    edges = edges * mask  # Apply mask to focus on center
    
    edges = np.expand_dims(edges, axis=-1)
    
    # Layer 4: Gradient magnitude (pieces have stronger gradients due to 3D shape)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_mag = np.sqrt(sobelx**2 + sobely**2)
    gradient_mag = (gradient_mag / gradient_mag.max()).astype(np.float32)
    gradient_mag = np.expand_dims(gradient_mag, axis=-1)
    
    # Combine all layers: [B, G, R, Edges, Gradients] = 5 channels
    enhanced = np.concatenate([bgr, edges, gradient_mag], axis=-1)
    
    return enhanced

# Load images and labels with enhanced preprocessing
def load_data():
    X, y = [], []
    
    print(f"Loading data from {DATASET_PATH}...")
    for label, category in enumerate(CATEGORIES):
        folder = os.path.join(DATASET_PATH, category)
        count = 0
        
        for filename in os.listdir(folder):
            if not filename.endswith('.png'):
                continue
                
            img_path = os.path.join(folder, filename)
            img = cv2.imread(img_path, cv2.IMREAD_COLOR)
            
            if img is None:
                print(f"[WARNING] Skipping invalid image: {img_path}")
                continue

            # Use enhanced preprocessing with edge detection
            img_processed = preprocess_image(img)
            X.append(img_processed)
            y.append(label)
            count += 1
        
        print(f"  Loaded {count} images from {category}")
    
    X = np.array(X)
    y = np.array(y)
    y = utils.to_categorical(y, num_classes=len(CATEGORIES))  # One-hot encoding
    
    print(f"\nTotal images loaded: {len(X)}")
    print(f"Image shape: {X[0].shape} (BGR + Edges + Gradients)")
    
    return X, y


# Load dataset
X, y = load_data()

# Split into training (80%) and validation (20%) sets
# Stratify ensures each class is proportionally represented in both sets
y_labels = np.argmax(y, axis=1)  # Convert one-hot back to labels for stratification
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y_labels
)

print(f"\nTraining samples: {len(X_train)}, Validation samples: {len(X_val)}")

# Calculate class weights to handle imbalance
# This makes the model pay more attention to underrepresented classes (white pieces)
y_train_labels = np.argmax(y_train, axis=1)
class_counts = np.bincount(y_train_labels)
total_samples = len(y_train_labels)
class_weights = {i: total_samples / (len(CATEGORIES) * class_counts[i]) 
                 for i in range(len(CATEGORIES))}

print(f"\nClass weights (to balance training):")
for i, category in enumerate(CATEGORIES):
    print(f"  {category}: {class_weights[i]:.2f}")

# Build new model with 5 input channels (BGR + Edges + Gradients)
print("\nBuilding CNN model for 5-channel input (multi-layer reasoning)...")
model_enhanced = models.Sequential([
    keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(64, 64, 5)),
    keras.layers.MaxPooling2D(2, 2),
    
    keras.layers.Conv2D(64, (3, 3), activation='relu'),
    keras.layers.MaxPooling2D(2, 2),
    
    keras.layers.Conv2D(128, (3, 3), activation='relu'),
    keras.layers.MaxPooling2D(2, 2),
    
    keras.layers.Flatten(),
    keras.layers.Dense(128, activation='relu'),
    keras.layers.Dropout(0.5),
    keras.layers.Dense(3, activation='softmax')
])

model_enhanced.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

print("\n" + "="*60)
print("TRAINING STARTED")
print("="*60)

# Train the model with class weights
history = model_enhanced.fit(
    X_train, y_train, 
    epochs=15,  # More epochs for better learning
    validation_data=(X_val, y_val),
    batch_size=32,
    class_weight=class_weights,  # Apply class weights
    verbose=1
)

# Save the trained model
model_enhanced.save("chess_piece_classifier_v7.h5")
print("\n[INFO] Model saved as chess_piece_classifier_v7.h5")

# Print training results
final_acc = history.history['accuracy'][-1]
val_acc = history.history['val_accuracy'][-1]
print("\n" + "="*60)
print("TRAINING COMPLETE")
print("="*60)
print(f"Final Training Accuracy: {final_acc:.4f}")
print(f"Final Validation Accuracy: {val_acc:.4f}")

# Test predictions on validation set
print("\nTesting on validation samples...")
y_pred = model_enhanced.predict(X_val[:20], verbose=0)
y_true = np.argmax(y_val[:20], axis=1)
y_pred_classes = np.argmax(y_pred, axis=1)

print("\nSample predictions:")
for i in range(20):
    true_label = CATEGORIES[y_true[i]]
    pred_label = CATEGORIES[y_pred_classes[i]]
    confidence = y_pred[i][y_pred_classes[i]] * 100
    status = "✓" if y_true[i] == y_pred_classes[i] else "✗"
    print(f"  {status} True: {true_label:12s} | Predicted: {pred_label:12s} | Confidence: {confidence:.1f}%")

print("\n" + "="*60)
print("IMPORTANT: Update main_inference_spacebar.py:")
print("  1. Change model load line to use v7")
print("  2. Update preprocessing to match multi-layer reasoning")
print("="*60)


