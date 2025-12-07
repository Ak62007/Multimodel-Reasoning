import os
from dotenv import load_dotenv
import whisper
import torch
from pyannote.audio import Pipeline

load_dotenv()

AUDIO_FILE = "./data/raw/Interview_2.wav"
HF_TOKEN = os.getenv('HUGGING_FACE')   # from https://huggingface.co/settings/tokens

# ---------- 1. TRANSCRIBE WITH WHISPER ----------
device = "cuda" if torch.cuda.is_available() else "cpu"
whisper_model = whisper.load_model("small", device=device)

whisper_result = whisper_model.transcribe(
    AUDIO_FILE,
    verbose=False,
    word_timestamps=False,   # set True if you want word-level later
)

whisper_segments = whisper_result["segments"]  # list of {start, end, text, ...}

# ---------- 2. DIARIZE WITH PYANNOTE ----------
# community-1 has an "exclusive" mode that plays nice with STT alignment
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token=HF_TOKEN,
)

pipeline.to(torch.device(device))

output = pipeline(AUDIO_FILE)

# exclusive_speaker_diarization = no overlapping speakers
diarization_turns = list(output.exclusive_speaker_diarization)


# ---------- 3. HELPER: ASSIGN SPEAKER TO WHISPER SEGMENT ----------
def assign_speaker_to_segment(seg, turns):
    """
    Pick speaker label based on the segment midpoint.
    """
    mid = 0.5 * (seg["start"] + seg["end"])
    for turn, speaker in turns:
        if turn.start <= mid <= turn.end:
            return speaker
    return "UNK"


# ---------- 4. MERGE: BUILD DIARIZED TRANSCRIPT ----------
diarized_segments = []
for seg in whisper_segments:
    speaker = assign_speaker_to_segment(seg, diarization_turns)
    diarized_segments.append(
        {
            "start": seg["start"],
            "end": seg["end"],
            "speaker": speaker,
            "text": seg["text"].strip(),
        }
    )

# ---------- 5. PRINT RESULT ----------
for seg in diarized_segments:
    print(
        f"[{seg['start']:6.2f} -> {seg['end']:6.2f}] {seg['speaker']}: {seg['text']}"
    )