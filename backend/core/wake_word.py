import queue
import sounddevice as sd
import json
import time
from vosk import Model, KaldiRecognizer
from difflib import SequenceMatcher

MODEL_PATH = "models/vosk-model-small-en-us-0.15"

WAKE_WORD_VARIANTS = [
    "hey drax",
    "hey drags",
    "hey tracks",
    "hey dracs",
    "hey dax",
    "hey cracks"
]

# cooldown config (Alexa-style)
COOLDOWN = 2  # seconds
last_trigger_time = 0

q = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status)
    q.put(bytes(indata))

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def listen_for_wake_word(on_wake_detected):
    global last_trigger_time

    print("🔵 Loading Vosk model...")
    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, 16000)
    recognizer.SetWords(True)


    print("🟢 Wake word listener active (say 'Hey Drax')")

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype="int16",
        channels=1,
        device=1,  # YOUR mic index
        callback=audio_callback,
    ):
        while True:
            data = q.get()
            
            if recognizer.AcceptWaveform(data) and len(data) > 4000:

                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()

                if not text:
                    continue

                print("Heard:", text)

                for variant in WAKE_WORD_VARIANTS:
                    if similar(variant, text) >= 0.75:
                        now = time.time()

                        # 🔒 cooldown guard
                        if now - last_trigger_time < COOLDOWN:
                            break

                        last_trigger_time = now
                        print("🟣 Wake word detected:", text)
                        on_wake_detected()
                        break
