import logging
import os
from typing import Optional
import anthropic
import pypandoc
from models import SystemPrompt, SystemSettings
from whisper import Whisper
from pydub import AudioSegment
import tempfile
import time


class _TranscriptionService:
    def __init__(self):
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')

        self.transcriber = Whisper()

        # Initialize Anthropic
        self.claude = anthropic.Anthropic(api_key=self.anthropic_api_key)

        self.isTranscribing = False

    def transcribe(self, file_path: str, output_path: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        self.isTranscribing = True
        try:
            # Load the audio file
            audio = AudioSegment.from_file(file_path)

            # Calculate the length of each segment (10 minutes = 600000 milliseconds)
            segment_length = 600000

            # Split the audio into 10-minute segments
            segments = [audio[i:i+segment_length] for i in range(0, len(audio), segment_length)]

            # Transcribe each segment
            transcripts = []
            for i, segment in enumerate(segments):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file_path = temp_file.name
                    segment.export(temp_file_path, format="wav")

                try:
                    transcript = self.transcriber.transcribe(temp_file_path)
                    transcripts.append(transcript['text'])
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
                            time.sleep(0.5)  # Wait half a second before retrying

            # Combine all transcripts
            full_transcript = " ".join(transcripts)

            # Write the combined transcript to the output file
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(full_transcript)

            return True, output_path, None

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return False, None, str(e)
        finally:
            self.isTranscribing = False


    def proofread(self, file_path: str, output_path: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                content = f.read()

            # Split content into parts with maximum 500 words each
            words = content.split()
            parts = []
            current_part = []
            word_count = 0

            for word in words:
                current_part.append(word)
                word_count += 1

                if word_count >= 500 and word.endswith('.'):
                    parts.append(' '.join(current_part))
                    current_part = []
                    word_count = 0

            if current_part:
                parts.append(' '.join(current_part))

            setting = SystemSettings.query.filter_by(setting_key='active_system_prompt_id').first()
            if not setting:
                raise ValueError("No active system prompt set")

            system_prompt = SystemPrompt.query.get(setting.setting_value)
            if not system_prompt:
                raise ValueError("Active system prompt not foun")
            
            # Process all parts
            processed_parts = []
            for part in parts:
                response = self.claude.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8192,
                    temperature=0,
                    system=system_prompt.prompt,
                    messages=[{"role": "user", "content": part}]
                )
                processed_parts.append(response.content[0].text)

            # Combine all processed parts
            combined_output = " ".join(processed_parts)

            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(combined_output)
            return True, output_path, None

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return False, None, str(e)

    def convert_to_docx(self, input_file: str, output_file: str, reference_doc: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            pypandoc.convert_file(
                input_file,
                'docx',
                outputfile=output_file,
                extra_args=['--reference-doc=' + reference_doc]
            )
            return True, output_file, None

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return False, None, str(e)

transcription_service = _TranscriptionService()