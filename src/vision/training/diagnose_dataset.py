import os
import cv2
import numpy as np

DATASET_PATH = "chess_dataset_v1"
CATEGORIES = ["empty", "black_piece", "white_piece"]

print("="*60)
print("CHESS DATASET DIAGNOSTIC")
print("="*60)

# Analyze dataset
for category in CATEGORIES:
    folder = os.path.join(DATASET_PATH, category)
    images = [f for f in os.listdir(folder) if f.endswith('.png')]
    
    print(f"\n{category.upper()}:")
    print(f"  Total images: {len(images)}")
    
    if len(images) > 0:
        # Sample 5 random images
        sample_images = np.random.choice(images, min(5, len(images)), replace=False)
        
        brightnesses = []
        contrasts = []
        
        for img_name in sample_images[:20]:  # Check first 20
            img_path = os.path.join(folder, img_name)
            img = cv2.imread(img_path)
            if img is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                brightnesses.append(np.mean(gray))
                contrasts.append(np.std(gray))
        
        if brightnesses:
            print(f"  Avg brightness: {np.mean(brightnesses):.1f} ± {np.std(brightnesses):.1f}")
            print(f"  Avg contrast: {np.mean(contrasts):.1f} ± {np.std(contrasts):.1f}")

print("\n" + "="*60)
print("RECOMMENDATION:")
print("="*60)

# Calculate class weights
total_images = sum([len([f for f in os.listdir(os.path.join(DATASET_PATH, cat)) if f.endswith('.png')]) 
                    for cat in CATEGORIES])

print("\nClass distribution:")
for i, category in enumerate(CATEGORIES):
    folder = os.path.join(DATASET_PATH, category)
    count = len([f for f in os.listdir(folder) if f.endswith('.png')])
    percentage = (count / total_images) * 100
    weight = total_images / (len(CATEGORIES) * count)
    print(f"  {category:12s}: {count:4d} images ({percentage:5.1f}%) - suggested weight: {weight:.2f}")

print("\n" + "="*60)

