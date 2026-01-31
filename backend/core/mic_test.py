import sounddevice as sd

print("Available microphones:\n")
print(sd.query_devices())

print("\nRecording 5 seconds... Speak now!")
audio = sd.rec(5 * 16000, samplerate=16000, channels=1, dtype="int16")
sd.wait()
print("Recording finished.")
