import logging
import os

from faster_whisper import WhisperModel
from typing import Optional
from models import ProofreadPrompt, SystemSetting
from pydub import AudioSegment
import tempfile
import time

from utils import measure_execution_time


class TranscriptionService:
    def __init__(self):
        self.model = WhisperModel("large-v3", device="auto", compute_type="auto")

    @measure_execution_time
    def transcribe(self, file_path: str, output_path: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            active_transcribe_prompt_setting = SystemSetting.query.filter_by(
                setting_key='active_transcribe_prompt_id').first()
            if not active_transcribe_prompt_setting:
                raise ValueError("No active transcribe prompt set")

            transcribe_prompt = ProofreadPrompt.query.get(
                active_transcribe_prompt_setting.setting_value)
            if not transcribe_prompt:
                raise ValueError("Active transcribe prompt not found")
            # Load the audio file
            audio = AudioSegment.from_file(file_path)

            # Calculate the length of each segment (10 minutes = 600000 milliseconds)
            segment_length = 600000

            # Split the audio into 10-minute segments
            segments = [audio[i:i+segment_length]
                        for i in range(0, len(audio), segment_length)]

            # Transcribe each segment
            transcripts = []
            for i, segment in enumerate(segments):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file_path = temp_file.name
                    segment.export(temp_file_path, format="wav")

                try:
                    segments, info = self.model.transcribe(temp_file_path, beam_size=5, language="id", task="transcribe", initial_prompt=transcribe_prompt.prompt)
                    logging.info("Detected language '%s' with probability %f" % (info.language, info.language_probability))
                    for segment in segments:
                        transcripts.append(segment.text)
                finally:
                    # Close the file handle explicitly
                    temp_file.close()

                    # Wait a short time to ensure the file is released
                    time.sleep(0.1)

                    # Attempt to delete the file, with retries
                    for _ in range(5):  # Try up to 5 times
                        try:
                            os.unlink(temp_file_path)
                            break
                        except PermissionError:
                            # Wait half a second before retrying
                            time.sleep(0.5)

            # Combine all transcripts
            full_transcript = " ".join(transcripts)

            # Write the combined transcript to the output file
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(full_transcript)

            return True, output_path, None

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return False, None, str(e)