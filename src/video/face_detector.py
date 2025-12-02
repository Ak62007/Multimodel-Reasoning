import cv2 as cv
import deepface as df
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)

def get_face_data(image_path, pad: float):
    """
    Input: Path to image
    Output:
        - face_crop: The cropped numpy array (ready for DeepFace)
        - landmarks: The raw mesh points (ready for Gaze Math)
    """
    
    img = cv.imread(image_path)
    # check
    if img is None:
        print(f"Error: Could not load {image_path}")
        return None, None
    
    h, w, _ = img.shape
    
    # convert to rgb and process it
    img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    # ready to be passed to get the face_mesh
    results = face_mesh.process(img_rgb)
    
    # check
    if not results.multi_face_landmarks:
        return None, None
    
    # Assuming one face
    landmarks = results.multi_face_landmarks[0].landmark
    
    # part-A calculating the bounding box from mesh
    
    # extract all x and y coordinates 
    x_coords = [p.x for p in landmarks]
    y_coords = [p.y for p in landmarks]
    
    x_min = int(min(x_coords) * w)
    x_max = int(max(x_coords) * w)
    y_min = int(min(y_coords) * h)
    y_max = int(max(y_coords) * h)
    
    # print("x_coords: ", x_coords)
    # print("y_coords: ", y_coords)
    
    # Applying the padding
    face_w = x_max - x_min
    face_h = y_max - y_min
    
    # 20% padding
    pad_x = int(face_w * pad)
    pad_y = int(face_h * pad)
    
    # applying padding with boundary checks
    crop_x1 = max(0, x_min - pad_x)
    crop_y1 = max(0, y_min - pad_y)
    crop_x2 = min(w, x_max + pad_x)
    crop_y2 = min(h, y_max + pad_y)
    
    # crop and return
    face_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
    
    return face_crop, landmarks
    