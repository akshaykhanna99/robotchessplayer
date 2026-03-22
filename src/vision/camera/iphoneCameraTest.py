import cv2
cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
print(cap.isOpened())
ret, frame = cap.read()
print(ret, None if frame is None else frame.shape)
cap.release()
