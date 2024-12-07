import whisper
from utils import measure_execution_time


class ASRModel:
    def __init__(self):
        self.model = whisper.load_model("turbo")

    @measure_execution_time
    def inference(self, file_path, language, initial_prompt):
        return self.model.transcribe(file_path, language=language, initial_prompt=initial_prompt)

