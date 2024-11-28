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

            with open(output_path, 'w') as file:
                file.write(transcript['text'])
            return True, output_path, None

        except Exception as e:
            print(f"An error occurred: {e}")
            return False, None, str(e)

    def proofread(self, file_path: str, output_path: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Split content into two parts
            content_length = len(content)
            mid_point = content_length // 2

            # Find the nearest period to create clean splits
            while mid_point < content_length and content[mid_point] != '.':
                mid_point += 1

            first_half = content[:mid_point + 1]
            second_half = content[mid_point + 1:]

            with open("system_prompt/v2.3.txt", "r") as f:
                system_prompt = f.read()

            # Process first half
            first_half_response = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": first_half}])
            first_half_result = first_half_response.content[0].text

            # Process second half
            second_half_response = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": second_half}])
            second_half_result = second_half_response.content[0].text

            # Combine responses
            combined_output = f"{first_half_result}\n{second_half_result}"

            with open(output_path, 'w') as file:
                file.write(combined_output)
            return True, output_path, None

        except Exception as e:
            print(f"An error occurred: {e}")
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
            print(f"An error occurred: {e}")
            return False, None, str(e)
