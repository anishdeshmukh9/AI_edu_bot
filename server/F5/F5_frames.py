import cv2


def extract_frames(video_path: str, every_sec: int = 5):
    cap = cv2.VideoCapture(video_path)
    frames = []
    sec = 0

    while cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ret, frame = cap.read()
        if not ret:
            break
        frames.append((sec, frame))
        sec += every_sec

    cap.release()
    return frames