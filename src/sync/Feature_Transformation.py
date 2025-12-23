import math
import librosa
import numpy as np
import pandas as pd
from typing import Literal, Union, Dict, List, Optional
from src.utils.datamodels import *

def blink_data(eyeblinkleft: float, eyeblinkright: float, eyesquintleft: float, eyesquintright: float, blinkweigth: float = 0.8, squintweigth: float = 0.2, mode: Literal["training", "evaluation"] = "training") -> Union[Dict, float]:
    """given the data this function returns Blink object that given info about the blinking of the user

    Args:
        eyeblinkleft (float): column: eyeBlinkLeft data
        eyeblinkright (float): column: eyeBlinkRight data
        eyesquintleft (float): column: eyeSquintLeft data
        eyesquintright (float): column: eyeSquintRight data
        blinkweigth (float, optional): weight on the blink. Defaults to 0.8.
        squintweigth (float, optional): weight on the squint. Defaults to 0.2.

    Returns:
        Blink: return Blink object or intensity of blink
    """
    left_closure = (eyeblinkleft * blinkweigth) + (eyesquintleft * squintweigth)
    right_closure = (eyeblinkright * blinkweigth) + (eyesquintright * squintweigth)
    
    avg_closure = (left_closure + right_closure)/2
    
    if mode == "training":
        return avg_closure
    else:
        is_closing = avg_closure > 0.5
        
        asymmetry = abs(left_closure - right_closure)
    
        result = {
            "blinking": is_closing,
            "asymmetry": asymmetry,
            "intensity": avg_closure
        }
        return result
    

def gaze_data(h_ratio: float, eyelookupleft: float, eyelookupright: float, eyelookdownleft: float, eyelookdownright: float, h_center: float = 0.5, h_dead_zone: float = 0.08, v_threshold: float = 0.15, mode: Literal["training", "evaluation"] = "training") -> Union[Dict, float]:
    """Gaze metrics for anomaly detection

    Args:
        h_ratio (float): 
        eyelookupleft (float): 
        eyelookupright (float): 
        eyeLookDownLeft (float): 
        eyelookdownright (float): 
        h_center (float, optional): Defaults to 0.5.
    
    Returns: Gaze object or gaze_magnitude
    """
    
    # horizontal deviation
    h_deviation = h_ratio - h_center
    
    # vertical metrics
    look_up = (eyelookupleft + eyelookupright)/2
    look_down = (eyelookdownleft + eyelookdownright)/2
    
    # Calculate intensities
    intensity_left = max(0.0, min(1.0, -h_deviation / 0.2))   
    intensity_right = max(0.0, min(1.0, h_deviation / 0.2))
    intensity_up = min(1.0, look_up / 0.6)
    intensity_down = min(1.0, look_down / 0.6)
    
    # Gaze magnitude (useful for anomaly detection)
    gaze_magnitude = (intensity_left + intensity_right + intensity_up + intensity_down)
    
    if mode == "training":
        return gaze_magnitude
    else:
        # Determine primary direction (priority: vertical > horizontal > center)
        if look_up > v_threshold:
            primary_direction = "up"
        elif look_down > v_threshold:
            primary_direction = "down"
        elif h_deviation < -(h_dead_zone):
            primary_direction = "left"
        elif h_deviation > h_dead_zone:
            primary_direction = "right"
        else:
            primary_direction = "center"
        result = {
            'horizontal_deviation': h_deviation,
            'vertical_deviation': look_up - look_down,
            'primary_direction': primary_direction
        }
        return result
    
def jaw_data(jaw_open: float, jaw_left: float, jaw_right: float, jaw_forward: float, mode: Literal["training", "evaluation"] = "training") -> Union[Dict, float]:
    """Jaw movement metrics for anomaly detection

    Args:
        jaw_open (float): 
        jaw_left (float): 
        jaw_right (float): 
        jaw_forword (float): 

    Returns:
        Union[Jaw, float]: jaw movement metrics or Jaw object
    """
    # Lateral movement
    jaw_lateral = jaw_right - jaw_left
    
    # Total jaw movement magnitude
    jaw_magnitude = jaw_open + abs(jaw_lateral) + jaw_forward
    
    if mode == "training":
        return jaw_magnitude
    else:
        result = {
            'open': jaw_open,
            'lateral': jaw_lateral,
            'forward': jaw_forward,
            'magnitude': jaw_magnitude,
            'is_open': jaw_open > 0.3
        }
        return result
    
def smile_data(mouthsmileleft: float, mouthsmileright: float, cheeksquintleft: float, cheeksquintright: float, mouthstretchleft: float, mouthstretchright: float, smile_weight: float = 0.7, squint_weight: float = 0.3, mode: Literal["training", "evaluation"] = "training") -> Union[Dict, float]:
    """Smile metrics for anomaly detection

    Args:
        mouthsmileleft (float): 
        mouthsmileright (float): 
        cheeksquintleft (float): 
        cheeksquintright (float): 
        mouthstretchleft (float): 
        mouthstretchright (float):
        smile_weight (float, optional): Defaults to 0.7.
        squint_weight (float, optional): Defaults to 0.3.

    Returns:
        Union[Smile, float]: smile intensity or Smile onject
    """
    
    # combined smile
    smile_left = mouthsmileleft * smile_weight + cheeksquintleft * squint_weight
    smile_right = mouthsmileright * smile_weight + cheeksquintright * squint_weight
    
    # intensity and asymmetry
    smile_intensity = (smile_left + smile_right )/2
    smile_asymmetry = abs(smile_left - smile_right)
    
    # mouth_stretch
    mouth_stretch = (mouthstretchleft + mouthsmileright)/2
    
    if mode == "training":
        return smile_intensity
    else:
        result = {
            'intensity': smile_intensity,
            'asymmetry': smile_asymmetry,
            'left_intensity': smile_left,
            'right_intensity': smile_right,
            'mouth_stretch': mouth_stretch,
            'is_smiling': smile_intensity > 0.3
        }
    return result

def loudness_level(rz: float) -> str:
    if rz <= -4.0: return "very_quiet"
    if rz <= -2.5: return "quiet"
    if rz <= 1.0:  return "normal"
    if rz <= 4.0:  return "loud"
    return "very_loud"

def pitch_relative_level(rz: float) -> str:
    if rz <= -3.5: return "much_lower"
    if rz <= -1.5: return "lower"
    if rz <= 1.5:  return "normal"
    if rz <= 3.5:  return "higher"
    return "much_higher"

def pitch_expressiveness_level(rz: float) -> str:
    if rz <= -2.5: return "flat"
    if rz <= -0.8: return "slightly_expressive"
    if rz <= 2.5:  return "expressive"
    return "highly_expressive"

def wps_level(rz: float) -> str:
    if rz <= -3.0: return "very_slow"
    if rz <= -1.5: return "slow"
    if rz <= 1.5:  return "normal"
    if rz <= 3.0:  return "fast"
    return "very_fast"


def compute_speaker_median_pitch(
    audio_path: str,
    speaker_segments: list,
    sr: int = 16000,
    fmin: float = 50.0,
    fmax: float = 600.0
):
    # loading the audio
    y, sr = librosa.load(audio_path, sr=sr)
    
    # Extracting pitch
    f0, voiced_flag, _ = librosa.pyin(
        y,
        fmin=fmin,
        fmax=fmax,
        sr=sr
    )
    
    # Frame timestamps
    times = librosa.times_like(f0, sr=sr)
    pitches = []
    
    for seg in speaker_segments:
        start, end = seg
        
        mask = (times >= start) & (times <= end)
        voiced_f0 = f0[mask]
        voiced_f0 = voiced_f0[~np.isnan(voiced_f0)]
        
        pitches.extend(voiced_f0.tolist())
        
    return round(float(np.median(pitches)) if pitches else None, 2)

def get_speaker_timings(speaker_times: pd.DataFrame, speaker: str) -> List[tuple[float, float]]:
    """Gives you the timing of the spreaker.

    Args:
        speaker_times (pd.DataFrame): dataframe with time and speaker columns
        speaker (str): which speaker time intervals you want

    Returns:
        List[tuple[float, float]]: Returns the time interval when the speaker has spoken
    """
    ss = speaker_times[~speaker_times['speaker'].isnull()].iloc[0]
    ss = tuple(ss)
    start_time, speaker_ = ss[0].item(), ss[1]
    timings = []
    for row in speaker_times.iterrows():
        row = tuple(row[1])
        if row[1] == None:
            continue
        elif (row[1] != speaker_):
            timings.append({speaker_: (start_time, row[0])})
            start_time = row[0]
            speaker_ = row[1]
            
    timings.append({speaker_: (start_time, row[0])})
    user_timings = [value for dic in timings for key, value in dic.items() if key == speaker]
    return user_timings

def audio_metrics_from_raw(
    audio_rms: float,
    pitch_avg_hz: float,
    pitch_var_hz2: float,
    speaker_median_pitch_hz: Optional[float] = None,
    eps: float = 1e-9
) -> Dict[str, float | bool | str]:
    """
    Convert raw audio features into interpretable metrics.

    Args:
        audio_rms: RMS energy (librosa.feature.rms)
        pitch_avg_hz: Average pitch in Hz (0 if unvoiced)
        pitch_var_hz2: Pitch variance in Hz^2 (0 if unvoiced)
        speaker_median_pitch_hz: Median pitch of speaker/session (recommended)
        eps: numerical stability

    Returns:
        Dict with meaningful audio metrics
    """

    is_voiced = pitch_avg_hz > 0.0

    # Loudness (RMS → dB)
    loudness_db = 20.0 * math.log10(audio_rms + eps)

    # Pitch (Hz → relative semitones)
    if is_voiced and speaker_median_pitch_hz and speaker_median_pitch_hz > 0:
        pitch_relative_st = 12.0 * math.log2(pitch_avg_hz / speaker_median_pitch_hz)
    else:
        pitch_relative_st = 0.0

    # Pitch expressiveness
    pitch_expressiveness_st = math.sqrt(pitch_var_hz2) if is_voiced else 0.0

    return {
        "is_voiced": is_voiced,
        "loudness_db": round(loudness_db, 2),
        "pitch_relative_st": round(pitch_relative_st, 2),
        "pitch_expressiveness_st": round(pitch_expressiveness_st, 2),
    }

def feature_engineering(c_anomalies: Optional[Dict[str, List[List[int]]]], anomalies: Optional[Dict[str, List[int]]], df: Optional[pd.DataFrame], norm_rz_df: Optional[pd.DataFrame], speaker_median_pitch: float, speaker: str, mode: Literal["training", "evaluation"]):
    """This Function transforms the current dataframe and joins and combines the features to create more meaningful features

    Args:
        c_anomalies (Optional[Dict[str, List[List[int]]]]): dictionary of continous anomaly times
        anomalies (Optional[Dict[str, List[int]]]): dictionary of all anomalous times for all features
        df (Optional[pd.DataFrame]): ori
        norm_rz_df (Optional[pd.DataFrame]): dataframe after feature creation, smoothing and normalization
        speaker_median_pitch (float): median pitch of the user
        speaker (str): user id for the speaker column
        mode (Literal[&quot;training&quot;, &quot;evaluation&quot;]): mode: training or evaluation

    Returns:
        pd.DataFrame: dataframe with feature engineered features or returns final dataframe to feed to the agentic architecture.
    """
    new_df = []
    for i in range(len(df)):
        
        # Visual Tranformed data
        
        # getting transformed blink data
        t_blink_data = blink_data(
            mode=mode,
            eyeblinkleft=df.iloc[i]['eyeBlinkLeft'],
            eyeblinkright=df.iloc[i]['eyeBlinkRight'],
            eyesquintleft=df.iloc[i]['eyeSquintLeft'],
            eyesquintright=df.iloc[i]['eyeSquintRight']
            )
        
        # getting transformed gaze data 
        t_gaze_data = gaze_data(
            mode=mode,
            eyelookdownleft=df.iloc[i]['eyeLookDownLeft'],
            eyelookdownright=df.iloc[i]['eyeLookDownRight'],
            eyelookupleft=df.iloc[i]['eyeLookUpLeft'],
            eyelookupright=df.iloc[i]['eyeLookUpRight'],
            h_ratio=df.iloc[i]['h_ratio']
        )
        
        # getting transformed jaw data
        t_jaw_data = jaw_data(
            mode=mode,
            jaw_open=df.iloc[i]['jawOpen'],
            jaw_forward=df.iloc[i]['jawForward'],
            jaw_left=df.iloc[i]['jawLeft'],
            jaw_right=df.iloc[i]['jawRight']
        )
        
        # getting transformed smile data
        t_smile_data = smile_data(
            mode=mode,
            mouthsmileleft=df.iloc[i]['mouthSmileLeft'],
            mouthsmileright=df.iloc[i]['mouthSmileRight'],
            mouthstretchleft=df.iloc[i]['mouthStretchLeft'],
            mouthstretchright=df.iloc[i]['mouthStretchRight'],
            cheeksquintleft=df.iloc[i]['cheekSquintLeft'],
            cheeksquintright=df.iloc[i]['cheekSquintRight']
        )
        
        if mode == "training":
            # Audio transformed data
            if df.iloc[i]['speaker'] == speaker:
                results = audio_metrics_from_raw(audio_rms=df.iloc[i]['audio_rms(volumn)'], pitch_avg_hz=df.iloc[i]['audio_pitch_avg'], pitch_var_hz2=df.iloc[i]['audio_pitch_var(expressiveness)'], speaker_median_pitch_hz=speaker_median_pitch)
                
                loudness_db = results['loudness_db']
                pitch_relative_st = results['pitch_relative_st']
                pitch_expressiveness_st = results['pitch_expressiveness_st']
            else:
                loudness_db = np.nan
                pitch_relative_st = np.nan
                pitch_expressiveness_st = np.nan
            
            new_row = {
                "blink_intensity": t_blink_data,
                "gaze_magnitude": t_gaze_data,
                "jaw_magnitude": t_jaw_data,
                "smile_intensity": t_smile_data,
                "loudness_db": loudness_db,
                "pitch_relative_st": pitch_relative_st,
                "pitch_expressiveness_st": pitch_expressiveness_st
            }
            
            new_df.append(new_row)
        else:
            b_is_anomalous = True if i in anomalies['blink_intensity_smooth_rz'] else False
            b_continuos_anomaly = any(i in anom for anom in c_anomalies['blink_intensity_smooth_rz'])
            b_part_of_anomalous_range = next((anom for anom in c_anomalies['blink_intensity_smooth_rz'] if i in anom), None)
            if b_is_anomalous:
                blink = Blink(
                    intensity=t_blink_data['intensity'],
                    asymmetry=t_blink_data['asymmetry'],
                    is_blinking=t_blink_data['blinking'],
                    rz_score=norm_rz_df.iloc[i]['blink_intensity_smooth_rz'],
                    is_anomalous=b_is_anomalous,
                    continuos_anomaly=b_continuos_anomaly,
                    part_of_anomalous_range=b_part_of_anomalous_range
                )
            else:
                blink = Blink(
                    is_blinking=t_blink_data['blinking'],
                    rz_score=norm_rz_df.iloc[i]['blink_intensity_smooth_rz'],
                    is_anomalous=b_is_anomalous,
                    continuos_anomaly=b_continuos_anomaly,
                    part_of_anomalous_range=b_part_of_anomalous_range
                )
            
            g_is_anomalous = True if i in anomalies['gaze_magnitude_smooth_rz'] else False
            g_continuos_anomaly = any(i in anom for anom in c_anomalies['gaze_magnitude_smooth_rz'])
            g_part_of_anomalous_range = next((anom for anom in c_anomalies['gaze_magnitude_smooth_rz'] if i in anom), None)
            if g_is_anomalous:
                gaze = Gaze(
                    horizontal_deviation=t_gaze_data['horizontal_deviation'],
                    vertical_deviation=t_gaze_data['vertical_deviation'],
                    primary_direction=t_gaze_data['primary_direction'],
                    rz_score=norm_rz_df.iloc[i]['gaze_magnitude_smooth_rz'],
                    is_anomalous=g_is_anomalous,
                    continuos_anomaly=g_continuos_anomaly,
                    part_of_anomalous_range=g_part_of_anomalous_range
                )
            else:
                gaze = Gaze(
                    primary_direction=t_gaze_data['primary_direction'],
                    rz_score=norm_rz_df.iloc[i]['gaze_magnitude_smooth_rz'],
                    is_anomalous=g_is_anomalous,
                    continuos_anomaly=g_continuos_anomaly,
                    part_of_anomalous_range=g_part_of_anomalous_range
                )
            
            j_is_anomalous = True if i in anomalies['jaw_magnitude_smooth_rz'] else False
            j_continuos_anomaly = any(i in anom for anom in c_anomalies['jaw_magnitude_smooth_rz'])
            j_part_of_anomalous_range = next((anom for anom in c_anomalies['jaw_magnitude_smooth_rz'] if i in anom), None)
            if j_is_anomalous:
                jaw = Jaw(
                    open=t_jaw_data['open'],
                    lateral=t_jaw_data['lateral'],
                    forward=t_jaw_data['forward'],
                    is_open=t_jaw_data['is_open'],
                    rz_score=norm_rz_df.iloc[i]['jaw_magnitude_smooth_rz'],
                    is_anomalous=j_is_anomalous,
                    continuos_anomaly=j_continuos_anomaly,
                    part_of_anomalous_range=j_part_of_anomalous_range
                )
            else:
                jaw = Jaw(
                    open=t_jaw_data['open'],
                    is_open=t_jaw_data['is_open'],
                    rz_score=norm_rz_df.iloc[i]['jaw_magnitude_smooth_rz'],
                    is_anomalous=j_is_anomalous,
                    continuos_anomaly=j_continuos_anomaly,
                    part_of_anomalous_range=j_part_of_anomalous_range
                )
                
            s_is_anomalous = True if i in anomalies['smile_intensity_smooth_rz'] else False
            s_continuos_anomaly = any(i in anom for anom in c_anomalies['smile_intensity_smooth_rz'])
            s_part_of_anomalous_range = next((anom for anom in c_anomalies['smile_intensity_smooth_rz'] if i in anom), None)
            if s_is_anomalous:
                smile = Smile(
                    intensity=t_smile_data['intensity'],
                    asymmetry=t_smile_data['asymmetry'],
                    left_intensity=t_smile_data['left_intensity'],
                    right_intensity=t_smile_data['right_intensity'],
                    mouth_stretch=t_smile_data['mouth_stretch'],
                    is_smiling=t_smile_data['is_smiling'],
                    rz_score=norm_rz_df.iloc[i]['smile_intensity_smooth_rz'],
                    is_anomalous=s_is_anomalous,
                    continuos_anomaly=s_continuos_anomaly,
                    part_of_anomalous_range=s_part_of_anomalous_range
                )
            else:
                smile = Smile(
                    intensity=t_smile_data['intensity'],
                    is_smiling=t_smile_data['is_smiling'],
                    rz_score=norm_rz_df.iloc[i]['smile_intensity_smooth_rz'],
                    is_anomalous=s_is_anomalous,
                    continuos_anomaly=s_continuos_anomaly,
                    part_of_anomalous_range=s_part_of_anomalous_range
                )
                
            # Audio 
            if norm_rz_df.iloc[i]['speaker'] == speaker:
                # loudness
                l_is_anomalous = True if i in anomalies['loudness_db_smooth_rz'] else False
                l_continuos_anomaly = any(i in anom for anom in c_anomalies['loudness_db_smooth_rz'])
                l_part_of_anomalous_range = next((anom for anom in c_anomalies['loudness_db_smooth_rz'] if i in anom), None)
                
                # pitch_avg
                pa_is_anomalous = True if i in anomalies['pitch_relative_st_smooth_rz'] else False
                pa_continuos_anomaly = any(i in anom for anom in c_anomalies['pitch_relative_st_smooth_rz'])
                pa_part_of_anomalous_range = next((anom for anom in c_anomalies['pitch_relative_st_smooth_rz'] if i in anom), None)
                
                # pitch_std
                ps_is_anomalous = True if i in anomalies['pitch_expressiveness_st_smooth_rz'] else False
                ps_continuos_anomaly = any(i in anom for anom in c_anomalies['pitch_expressiveness_st_smooth_rz'])
                ps_part_of_anomalous_range = next((anom for anom in c_anomalies['pitch_expressiveness_st_smooth_rz'] if i in anom), None)
                
                # wps
                w_is_anomalous = True if i in anomalies['wps_smooth_rz'] else False
                w_continuos_anomaly = any(i in anom for anom in c_anomalies['wps_smooth_rz'])
                w_part_of_anomalous_range = next((anom for anom in c_anomalies['wps_smooth_rz'] if i in anom), None)
                
                # filler words usage
                f_is_anomalous = True if i in anomalies['filler_percentage'] else False
                f_continuos_anomaly = any(i in anom for anom in c_anomalies['filler_percentage'])
                f_part_of_anomalous_range = next((anom for anom in c_anomalies['filler_percentage'] if i in anom), None)
                
                # pause taken
                p_is_anomalous = True if i in anomalies['pause_percent_pr'] else False
                p_continuos_anomaly = any(i in anom for anom in c_anomalies['pause_percent_pr'])
                p_part_of_anomalous_range = next((anom for anom in c_anomalies['pause_percent_pr'] if i in anom), None)
                
                loudnesstate = LoudnessState(
                    level=loudness_level(rz=norm_rz_df.iloc[i]['loudness_db_smooth_rz']),
                    rz_score=norm_rz_df.iloc[i]['loudness_db_smooth_rz'],
                    is_anomalous=l_is_anomalous,
                    continuos_anomaly=l_continuos_anomaly,
                    part_of_anomalous_range=l_part_of_anomalous_range
                )
                
                pitchstate = PitchState(
                    relative_level=pitch_relative_level(rz=norm_rz_df.iloc[i]['pitch_relative_st_smooth_rz']),
                    rz_score=norm_rz_df.iloc[i]['pitch_relative_st_smooth_rz'],
                    is_anomalous=pa_is_anomalous,
                    continuos_anomaly=pa_continuos_anomaly,
                    part_of_anomalous_range=pa_part_of_anomalous_range
                )
                
                pitchstd = PitchStd(
                    expressiveness=pitch_expressiveness_level(rz=norm_rz_df.iloc[i]['pitch_expressiveness_st_smooth_rz']),
                    rz_score=norm_rz_df.iloc[i]['pitch_expressiveness_st_smooth_rz'],
                    is_anomalous=ps_is_anomalous,
                    continuos_anomaly=ps_continuos_anomaly,
                    part_of_anomalous_range=ps_part_of_anomalous_range
                )
                
                wps = WPS(
                    speaking_rate=wps_level(rz=norm_rz_df.iloc[i]["wps_smooth_rz"]),
                    rz_score=norm_rz_df.iloc[i]["wps_smooth_rz"],
                    is_anomalous=w_is_anomalous,
                    continuous_anomaly=w_continuos_anomaly,
                    part_of_anomalous_range=w_part_of_anomalous_range
                )
                
                fillerpercentageincrease = FillerPercentageIncrease(
                    filler_percentage_level="abnormally high" if f_is_anomalous else "normal",
                    is_anomalous=f_is_anomalous,
                    continuous_anomaly=f_continuos_anomaly,
                    part_of_anomalous_range=f_part_of_anomalous_range
                )
                
                pausepercentageincrease = PausePercentageIncrease(
                    pause_percentage_level="abnormally high" if p_is_anomalous else "normal",
                    is_anomalous=p_is_anomalous,
                    continuous_anomaly=p_continuos_anomaly,
                    part_of_anomalous_range=p_part_of_anomalous_range
                )
                
                # new_row
                new_row = {
                    "blinking_data": blink.model_dump(),
                    "gaze_data": gaze.model_dump(),
                    "jaw_movement_data": jaw.model_dump(),
                    "smile_data": smile.model_dump(),
                    "loudness_data": loudnesstate.model_dump(),
                    "average_pitch_data": pitchstate.model_dump(),
                    "pitch_standard_deviation": pitchstd.model_dump(),
                    "words_per_sec": wps.model_dump(),
                    "filler_words_usage": fillerpercentageincrease.model_dump(),
                    "pauses_taken": pausepercentageincrease.model_dump()
                }
            else:
                # new_row
                new_row = {
                    "blinking_data": blink.model_dump(),
                    "gaze_data": gaze.model_dump(),
                    "jaw_movement_data": jaw.model_dump(),
                    "smile_data": smile.model_dump(),
                    "loudness_data": np.nan,
                    "average_pitch_data": np.nan,
                    "pitch_standard_deviation": np.nan,
                    "words_per_sec": np.nan,
                    "filler_words_usage": np.nan,
                    "pauses_taken": np.nan
                }

            new_df.append(new_row)
            
    # Creating the the new dataframe
    new_df = pd.DataFrame(new_df)
    return new_df
        