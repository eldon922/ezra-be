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

            system_prompt = """I want you to be my assistant to help me with creating transcript of sermons, I have used Whisper model to convert the speech into text. Go through these texts and modify them so they:\r\n1. Follow the correct language rules without modifying any words (except it is mistyped, please fix it), change the structure, reorder words in sentences.\r\n2. Proper (not short) paragraphing. Please be mind that I will use this texts to create short form video content maximum 1 minutes. So please do the paragraphing by minding it and don't create too short paragraph.\r\n3. Fixing mistyped words\r\n4. Applying italics to foreign language words rather than the main language.\r\n5. Separate each Bible verse onto its own line and make the text italic, then add a superscript number at the beginning of each line to indicate the verse number using ^TEXT^ format.\r\n6. Use double quote for each references that the speaker spoke which are comes from other sources.\r\n7. Add, change, or remove punctuations so it is used properly, such as using em dashes on appropriate places, semi colon, etc.\r\n8. Change \"Bapak\" to \"Bapa\" if it's refer to Father. If it's not, use \"Bapak\".\r\n9. Add double quotes to prayer.\r\n\r\nThere are rules that you need to comply when you do the modification on the text which are:\r\n1. Please don't remove any words or sentences or changing it.\r\n2. Don't come up with new words or something else.\r\n\r\nPlease, generate the markdown output only. No need any response from you other than that."""

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
