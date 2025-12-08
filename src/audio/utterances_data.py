import pandas as pd
import assemblyai as aai

def get_utterances_data(api_key: str, audio_path: str) -> pd.DataFrame:

    aai.settings.api_key = api_key

    print("Uploading and transcribing...")
    transcriber = aai.Transcriber()

    transcript = transcriber.transcribe(
        audio_path, 
        config=aai.TranscriptionConfig(speaker_labels=True)
    )

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f'Transcription failed: {transcript.error}')
    else:
        print("Transcription complete!")
        
        # let's convert this into a dataframe
        utt_data = []
        for utt in transcript.utterances:
            row = {
                'text': utt.text,
                'start': utt.start,
                'end': utt.end,
                'confidence': utt.confidence,
                'speaker': utt.speaker,
                'channel': utt.channel,
                'words': utt.words,
                'translated_texts': utt.translated_texts
            }
            utt_data.append(row)
            
        utt_data = pd.DataFrame(utt_data)
        return utt_data