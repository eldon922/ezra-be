import time
from faster_whisper import WhisperModel


def measure_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time of {func.__name__}: {
              execution_time:.6f} seconds")
        return result

    return wrapper


class Whisper:
    def __init__(self):
        model_size = "medium"

        # Run on GPU with FP16
        self.model = WhisperModel(
            model_size, device="auto", compute_type="auto")

    @measure_execution_time
    def transcribe(self, file_path):
        segments, info = self.model.transcribe(
            file_path, beam_size=5, language="id")
        print("Detected language '%s' with probability %f" %
              (info.language, info.language_probability))
        return segments
