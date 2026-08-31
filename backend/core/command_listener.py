import speech_recognition as sr

def listen_for_command_speech(timeout=6, phrase_limit=8) -> str:
    """
    Captures voice input from the microphone using Google Speech Recognition.
    Returns recognized text in lowercase or empty string if unheard.
    """
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8

    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.6)
            print("🎤 DRAX Listening...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        
        text = recognizer.recognize_google(audio).lower().strip()
        print(f"🗣️ Heard: {text}")
        return text
    except sr.WaitTimeoutError:
        print("⏱️ Listening timed out.")
        return ""
    except sr.UnknownValueError:
        print("❓ Speech unrecognized.")
        return ""
    except Exception as e:
        print(f"⚠️ Speech listener error: {e}")
        return ""