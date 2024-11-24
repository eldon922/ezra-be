import os
from pathlib import Path
import assemblyai as aai
import anthropic
import pypandoc
from typing import Optional

class TranscriptionService:
    def __init__(self):
        self.aai_api_key = os.environ.get('AAI_API_KEY')
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        
        # Initialize AssemblyAI
        aai.settings.api_key = self.aai_api_key
        self.config = aai.TranscriptionConfig(
            language_code="id",
            disfluencies=True
        )
        self.transcriber = aai.Transcriber(config=self.config)
        
        # Initialize Anthropic
        self.claude = anthropic.Anthropic(api_key=self.anthropic_api_key)

    def transcribe(self, file_path: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            transcript = self.transcriber.transcribe(file_path)
            if transcript.status == aai.TranscriptStatus.error:
                return False, None, str(transcript.error)

            output_path = f'{Path(file_path).stem}.md'
            with open(output_path, 'w') as file:
                file.write(transcript.text)
            return True, output_path, None
            
        except Exception as e:
            return False, None, str(e)

    def proofread(self, file_path: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            with open(file_path, "r") as f:
                content = f.read()

            system_prompt = """I want you to be my assistant to help me with creating transcript of sermons, I have used Whisper model to convert the speech into text. Go through these texts and modify them so they:\n1. Follow the correct language rules without modifying any words (except it is mistyped, please fix it), change the structure, reorder words in sentences.\n2. Proper (not short) paragraphing. Please be mind that I will use this texts to create short form video content maximum 1 minutes. So please do the paragraphing by minding it and don't create too short paragraph.\n3. Fixing mistyped words\n4. Applying italics to foreign language words rather than the main language.\n5. Separate each Bible verse onto its own line and make the text italic, then add a superscript number at the beginning of each line to indicate the verse number.\n6. Use double quote for each references that the speaker spoke which are comes from other sources.\n7. Add, change, or remove punctuations so it is used properly, such as using em dashes on appropriate places, semi colon, etc.\n\nThere are rules that you need to comply when you do the modification on the text which are:\n1. Please don't remove any words or sentences or changing it.\n2. Don't come up with new words or something else.\n\nPlease, create the markdown output only. No need any response from you other than that."""

            message = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=30000,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": [{"type": "text", "text": content}]}]
            )

            output_path = f'{Path(file_path).stem}_proofread.md'
            with open(output_path, 'w') as file:
                file.write(message.content)
            return True, output_path, None

        except Exception as e:
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
            return False, None, str(e)