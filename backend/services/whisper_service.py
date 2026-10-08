import whisper


print("Loading Whisper model...")

model = whisper.load_model("base")

print("Whisper model loaded successfully.")


def transcribe_audio(audio_file: str):

    result = model.transcribe(
        audio_file,
        task="transcribe"
    )

    return {
        "text": result["text"].strip(),
        "language": result.get("language", "unknown")
    }