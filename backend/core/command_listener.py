import queue
import sounddevice as sd
import json
from vosk import Model, KaldiRecognizer

MODEL_PATH = "models/vosk-model-small-en-us-0.15"
q = queue.Queue()

def audio_callback(indata, frames, time, status):
    q.put(bytes(indata))

def listen_for_command():
    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, 16000)
    recognizer.SetWords(True)

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype="int16",
        channels=1,
        device=1,
        callback=audio_callback,
    ):
        while True:
            data = q.get()
            if recognizer.AcceptWaveform(data) and len(data) > 4000:
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()
                print("Command heard:", text)
                return text
