import logging
from typing import Optional
import pypandoc


class PandocService:
    def convert_to_docx(self, input_file: str, output_file: str, reference_doc: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                input_text = f.read()
            
            pypandoc.convert_text(
                input_text,
                'docx',
                format='markdown',
                outputfile=output_file,
                extra_args=['--reference-doc=' + reference_doc]
            )
            return True, output_file, None

        except Exception as e:
            return False, None, str(e)
