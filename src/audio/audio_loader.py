from moviepy import VideoFileClip
import os

def extract_audio(video_path: str, output_dir: str = "../data/raw/", output_ext='.wav'):
    """
    Extracts audio from the video and saves it as a WAV file. 
    """
    # create the output directory if it does not exist
    os.makedirs(output_dir, exist_ok=True)
    
    # generate the file name
    filename = os.path.basename(video_path).split('.')[0]
    output_path = os.path.join(output_dir, f'{filename}.{output_ext}')
    
    if os.path.exists(output_path):
        print(f"Audio already exists at : {output_path}")
        return output_path
    
    try:
        video_clip = VideoFileClip(video_path)
        
        if video_clip.audio is None:
            print("Error: This video has no sound")
            return None
        
        video_clip.audio.write_audiofile(output_path, logger='bar')
        video_clip.close()
        return output_path
    except Exception as e:
        print(f"Error: {e}")
        return None