import whisper_timestamped as wp
import pandas as pd

def get_whisper_data(audio_path: str, model_size: str = 'small', lang: str = None, device: str = 'cpu'):
    
    # load audio and model
    audio = wp.load_audio(file=audio_path)
    model = wp.load_model(model_size, device=device)
    
    # get results
    result = wp.transcribe_timestamped(
    model=model,
    audio=audio,
    language=lang,
    detect_disfluencies=True
    )
    
    tr_df = pd.DataFrame(result["segments"])
    
    return tr_df