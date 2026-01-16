import cv2

cap = cv2.VideoCapture(0)
fps = cap.get(cv2.CAP_PROP_FPS)  # Get FPS from the webcam

print(f"Webcam FPS: {fps}")

# Force FPS to 30
cap.set(cv2.CAP_PROP_FPS, 30)
print(f"new Webcam FPS: {fps}")


cap.release()
cv2.destroyAllWindows()
