from app.asr.transcriber import Transcriber


transcriber = Transcriber()

result = transcriber.transcribe("test.m4a", num_speakers=3)

print("\n========== DIARIZED TRANSCRIPT ==========\n")
print(result["transcript"])

print("\n========== SPEAKER TURNS ==========\n")

for turn in result["speaker_turns"]:
    print(
        f"[{turn['start']:.2f} -> {turn['end']:.2f}] "
        f"{turn['speaker']}: {turn['text']}"
    )
