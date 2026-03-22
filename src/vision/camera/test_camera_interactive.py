#!/usr/bin/env python3
"""
Interactive camera test - shows one camera at a time
Press 'q' to close and try the next camera
"""
import cv2
import sys

print("Interactive Camera Test")
print("=" * 50)
print("Instructions:")
print("  - Each camera will open in a window")
print("  - Press 'q' to close and try next camera")
print("  - Press 'ESC' to exit completely")
print("=" * 50)
print()

# Try different camera indices
for i in range(5):
    print(f"\n{'='*50}")
    print(f"Testing Camera Index: {i}")
    print(f"{'='*50}")
    
    cap = cv2.VideoCapture(i)
    
    if not cap.isOpened():
        print(f"✗ Camera {i} failed to open")
        continue
    
    # Try to read a frame
    ret, frame = cap.read()
    if not ret:
        print(f"✗ Camera {i} opened but cannot capture frames")
        cap.release()
        continue
    
    print(f"✓ Camera {i} is working!")
    print(f"  Resolution: {frame.shape[1]}x{frame.shape[0]}")
    print(f"\n  Press 'q' to try next camera")
    print(f"  Press 'ESC' to exit")
    
    # Show live feed
    window_name = f"Camera {i} - Press 'q' for next, ESC to exit"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame")
            break
        
        # Add text overlay
        cv2.putText(frame, f"Camera Index: {i}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Resolution: {frame.shape[1]}x{frame.shape[0]}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "Press 'q' for next camera, ESC to exit", (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.imshow(window_name, frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print(f"Moving to next camera...")
            break
        elif key == 27:  # ESC key
            print(f"\nExiting. Use camera index {i} in your main script.")
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)
    
    cap.release()
    cv2.destroyAllWindows()

print("\n" + "="*50)
print("Finished testing all cameras")
print("="*50)

