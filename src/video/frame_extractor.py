import cv2 as cv
import numpy as np
import os

def extract_frames(video_path, output_path):
    """
    input:
        video_path - path to the video.
        output_path - path where to save the frames.
    
    output:
        - returns a list of frame paths and there timings when they appear
    """
    result = []
    vid = cv.VideoCapture(video_path)
    
    # check we got the video
    if not vid.isOpened():
        print("Cannot open video")
        exit()
        
    # let's calculate the total duration of the video
    fps = vid.get(cv.CAP_PROP_FPS)
    total_frame = vid.get(cv.CAP_PROP_FRAME_COUNT)
    vid_duration = (total_frame/fps) * 1000
    
    # start at 0 milisecs
    current_time_ms = 0
    frame_cnt = 0
    
    while True:
        # check of the video is ended then break if false
        if current_time_ms < vid_duration:
            # jump to specific time
            vid.set(cv.CAP_PROP_POS_MSEC, current_time_ms)
            
            # read the frame
            ret, frame = vid.read()
            
            # getting the current time 
            time_frame = current_time_ms/1000
            
            # save the frame
            path = f"{output_path}/{frame_cnt+1}_ts_{time_frame}.jpg"
            cv.imwrite(path, frame)
            
            frame_cnt += 1
            current_time_ms += 1000
            
            result.append((path, time_frame))
        else:
            break
    
    return result