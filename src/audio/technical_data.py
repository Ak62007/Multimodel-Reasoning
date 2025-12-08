import librosa
import numpy as np
import pandas as pd
import os

def analyze_audio_layers(audio_path: str, segment_length: float=0.5) -> pd.DataFrame:
    """
    Input: 
        audio_path: path to the audio file
        segment_length: time window in secs (same as video dataframe)
    Output:
        au_data: dataframe with TS features for analysis (Ready to go to the data analysis pipeline)
    """
    # check is the audio file exists
    if not os.path.exists(audio_path):
        print(f"Error: {audio_path} does not exit")
        return None
    
    # loading audio file
    y, sr = librosa.load(audio_path, sr=None)
    
    # total duration
    total_duration = librosa.get_duration(y=y, sr=sr)
    
    au_data = []
    
    # iterating through the audio chunks
    for t in np.arange(0, total_duration, segment_length):
        
        # calculating the starting and ending indexes for this chunk
        start_sample = int(t * sr)
        end_sample = int((t + segment_length)*sr)
        
        # getting the chunk for this iteration
        chunk = y[start_sample:end_sample]
        
        # check if the file ended
        if len(chunk) == 0: break
        
        # FEATURE - 1: AMPLITUDE (Confidence/Volume)
        rms = np.mean(librosa.feature.rms(y=chunk))
        
        # FEATURE - 2: SILENCE DETECTION
        # Threshold: 0.005 is a standard "noise floor" for webcams
        is_silent = rms < 0.005
        
        # FEATURE 3 & 4: PITCH TRACKING (Monotone vs Expressive)
        avg_pitch = 0
        pitch_var = 0
        
        # if not silent
        if not is_silent:
            f0, voiced_flag, _ = librosa.pyin(
                chunk,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C5'),
                sr=sr,
                frame_length=2048
            )
            
            # filtering out the NaNs (moments of unvoiced sound)
            valid_pitch = f0[~np.isnan(f0)]
            
            if len(valid_pitch) > 0:
                avg_pitch = np.mean(valid_pitch)
                # I think this is super cool this pitch var effectively measures you expressiveness
                pitch_var = np.std(valid_pitch) 
                
        # creating the row
        au_data.append({
            "Time": round(t, 2),
            "audio_rms(volumn)": round(rms, 4),
            "audio_pitch_avg": round(avg_pitch, 2),
            "audio_pitch_var(expressiveness)": round(pitch_var, 2),
            "is_silent": is_silent
        })
        
    # converting into a dataframe
    au_data = pd.DataFrame(au_data)
    au_data = au_data.sort_values('Time').reset_index(drop=True)
    
    return au_data
                  