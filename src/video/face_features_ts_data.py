import os
import math
import pandas as pd
# import numpy as np
import mediapipe as mp
from pathlib import Path
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

def get_coordinates(landmarks: list, idx: int) -> tuple:
    return (landmarks[idx].x, landmarks[idx].y)

def euclidean_distance(coord1: tuple, coord2: tuple) -> float:
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)


def calculate_gaze_ratios(landmarks: list) -> tuple:
    """
    Inputs:
        landmarks: resultant landmarks coordinates of all the important points on the face.
    Output:
        returns: (horizontal gaze ratio, vertical gaze ratio)
    """
    # important indexes in the landmark result.
    # RIGHT EYE (User's Right)
    R_IRIS_CENTER = 468
    R_INNER_CORNER = 133  # Toward nose
    R_OUTER_CORNER = 33   # Toward ear
    # R_TOP_LID = 159
    # R_BOTTOM_LID = 145

    # LEFT EYE (User's Left)
    L_IRIS_CENTER = 473
    L_INNER_CORNER = 362  # Toward nose
    L_OUTER_CORNER = 263  # Toward ear
    # L_TOP_LID = 386
    # L_BOTTOM_LID = 374
    
    # Calculating Horizontal Gaze ratio
    # For right eye
    # getting important coordinates
    r_iris_center_coor = get_coordinates(landmarks=landmarks, idx=R_IRIS_CENTER)
    r_inner_corner_coor = get_coordinates(landmarks=landmarks, idx=R_INNER_CORNER)
    r_outer_corner_coor = get_coordinates(landmarks=landmarks, idx=R_OUTER_CORNER)
    
    # getting the distances
    r_inner_d = euclidean_distance(coord1=r_iris_center_coor, coord2=r_inner_corner_coor)
    r_outer_inner_d = euclidean_distance(coord1=r_inner_corner_coor, coord2=r_outer_corner_coor)
    
    # right eye ratio
    rh_ratio = r_inner_d/r_outer_inner_d
    
    # for left eye
    # getting important coordinates
    l_iris_center_coor = get_coordinates(landmarks=landmarks, idx=L_IRIS_CENTER)
    l_inner_corner_coor = get_coordinates(landmarks=landmarks, idx=L_INNER_CORNER)
    l_outer_corner_coor = get_coordinates(landmarks=landmarks, idx=L_OUTER_CORNER)
    
    # getting the distances
    l_outer_d = euclidean_distance(coord1=l_iris_center_coor, coord2=l_outer_corner_coor)
    l_outer_inner_d = euclidean_distance(coord1=l_inner_corner_coor, coord2=l_outer_corner_coor)
    
    # left eye ratio
    lh_ratio = l_outer_d/l_outer_inner_d
    
    # horizontal gaze ratio
    h_ratio = (rh_ratio + lh_ratio)/2
    
    # Calculating Vertical Gaze ratio
    # for right eye
    ry_center = (r_inner_corner_coor[1] + r_outer_corner_coor[1])/2
    r_offset = r_iris_center_coor[1] - ry_center
    rv_ratio = r_offset/r_outer_inner_d
    
    # for left eye
    ly_center = (l_inner_corner_coor[1] + l_outer_corner_coor[1])/2
    l_offset = l_iris_center_coor[1] - ly_center
    lv_ratio = l_offset/l_outer_inner_d
    
    # vertical gaze ratio
    v_ratio = (rv_ratio + lv_ratio)/2
    
    return (h_ratio, v_ratio)

def face_analysis_data(model_path, images_path) -> pd.DataFrame:
    """
    Inputs:
        model_path - mediapipe model weights file path
        images_path - path of the files where we saved the frame by frame images of the video.
    
    Output:
        fa_data - Time-Series data about the face emotions changing frame by frame in the video.
    """
    # Initializing the DataFrame
    fa_data = []
    
    folder = Path(images_path)
    
    if not folder.exists():
        print(f"Folder {images_path} does not exist")
        return
    
    # This just let's mediapipe know where is the .task(model) weights of the model
    base_options = python.BaseOptions(model_asset_path=model_path)
    
    # Start the Face detector engine
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        # output_face_landmarks=True,
        num_faces=1,
        min_face_detection_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE
    )
    
    # initialize the detector
    detector = vision.FaceLandmarker.create_from_options(options)
    
    # iterating from the image paths
    for filepath in folder.iterdir():
        timing = float(filepath.stem.split("_ts_")[1])
        image = mp.Image.create_from_file(filepath.as_posix())
        results = detector.detect(image)
        
        if not results.face_landmarks or len(results.face_landmarks) == 0:
            print(f"no face detected in the frame : {filepath.as_posix()}")
            row = {
                'Time': timing,
                # 'h_ratio': np.nan,
                # 'v_ratio': np.nan,
            }
            
            fa_data.append(row)
            continue
        
        landmarks = results.face_landmarks[0]
        h_gaze_ratio, v_gaze_ratio = calculate_gaze_ratios(landmarks=landmarks)
        
        if results.face_blendshapes and len(results.face_blendshapes) > 0:
            blend_shapes = results.face_blendshapes[0]
        else:
            blend_shapes = []
        
        # filling the dataframe
        row = {
            'Time': timing,
            'h_ratio': h_gaze_ratio,
            'v_ratio': v_gaze_ratio
        }
        
        if len(blend_shapes) == 0:
            fa_data.append(row)
        else:
            for feature in blend_shapes:
                row[feature.category_name] = feature.score
            fa_data.append(row)

    # Let's build the dataframe
    fa_data = pd.DataFrame(fa_data)
    fa_data = fa_data.sort_values('Time').reset_index(drop=True)
    
    return fa_data