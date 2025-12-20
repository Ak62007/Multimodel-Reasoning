from typing import Literal, Union, Dict

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