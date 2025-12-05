from cv2 import cv
import numpy as np

def draw_landmarks_on_image(rgb_image, detection_result):
    """
    Inputs:
      rgb_image: The numpy array of the image (height, width, 3)
      detection_result: The result object from FaceLandmarker
    Output:
      annotated_image: Image with dots drawn on it
    """
    face_landmarks_list = detection_result.face_landmarks
    
    # Create a copy so we don't modify the original
    annotated_image = np.copy(rgb_image)
    height, width, _ = annotated_image.shape

    # Loop through all faces (usually just 1)
    for face_landmarks in face_landmarks_list:
        
        # 1. Draw ALL 478 points (Small Green Dots)
        for idx, landmark in enumerate(face_landmarks):
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            
            # Draw tiny green dot
            cv.circle(annotated_image, (x, y), 1, (0, 255, 0), -1)

        # 2. Highlight GAZE Points (Large Red Dots)
        # These are the specific indices we use for the Ratio Math
        # [Iris, Inner, Outer, Top, Bottom] for both eyes
        gaze_indices = [
            468, 473,       # Irises
            263, 362,       # Left Eye Horizontal
            33, 133,        # Right Eye Horizontal
            386, 374,       # Left Eye Vertical
            159, 145        # Right Eye Vertical
        ]
        
        for idx in gaze_indices:
            landmark = face_landmarks[idx]
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            
            # Draw larger Red dot
            cv.circle(annotated_image, (x, y), 3, (255, 0, 0), -1)

    return annotated_image