from app.asr.transcriber import Transcriber


transcriber = Transcriber()

result = transcriber.transcribe('test.m4a')

print('\n ========= Transcribe ==========')
print(result['transcript'])

print('\n ========== Segments ==========')

for segment in result['segments']:
    print(
        f"[{segment['start']:.2f} -> {segment['end']:.2f}] "
        f"{segment['text']}"
    )