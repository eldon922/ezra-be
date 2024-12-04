import logging
import os
from typing import Optional

import anthropic
import pypandoc

from whisper import Whisper


class TranscriptionService:
    def __init__(self):
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')

        self.transcriber = Whisper()

        # Initialize Anthropic
        self.claude = anthropic.Anthropic(api_key=self.anthropic_api_key)

    def transcribe(self, file_path: str, output_path: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            transcript = self.transcriber.transcribe(file_path)
            # if transcript.status == aai.TranscriptStatus.error:
            #     return False, None, str(transcript.error)

            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(transcript['text'])
            return True, output_path, None

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return False, None, str(e)

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

            with open("system_prompt/v3.1.txt", "r", encoding='utf-8') as f:
                system_prompt = f.read()

            # Process all parts
            processed_parts = []
            for part in parts:
                response = self.claude.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8192,
                    temperature=0,
                    system=system_prompt,
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
