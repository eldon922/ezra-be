import logging
import os
from typing import Optional
import anthropic
import asyncio
from models import ProofreadPrompt, SystemSetting, Transcription
from database import db
from openai import AsyncOpenAI, OpenAI


class ProofreadingService:
    def __init__(self):
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        self.deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY')
        self.deepseek_base_url = os.environ.get('DEEPSEEK_BASE_URL')

        # Initialize Anthropic
        self.claude = anthropic.Anthropic(api_key=self.anthropic_api_key)
        self.async_deepseek = AsyncOpenAI(api_key=self.deepseek_api_key, base_url=self.deepseek_base_url)

    async def process_part(self, part: str, prompt: str) -> str:
        # response = self.claude.messages.create(
        #     model="claude-3-5-sonnet-20241022",
        #     max_tokens=8192,
        #     temperature=0,
        #     system=proofread_prompt.prompt,
        #     messages=[{"role": "user", "content": part}]
        # )
        # processed_parts.append(response.content[0].text)
        """Process a single part of text asynchronously"""
        response = await self.async_deepseek.chat.completions.create(
            model="deepseek-reasoner",
            max_tokens=8192,
            temperature=0,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": part}
            ],
            stream=False
        )
        return response.choices[0].message.content

    async def process_all_parts(self, parts: list[str], prompt: str) -> list[str]:
        """Process all parts concurrently while maintaining order"""
        tasks = [self.process_part(part, prompt) for part in parts]
        results = await asyncio.gather(*tasks)
        return results

    def proofread(self, transcription: Transcription, output_path: str) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            with open(transcription.txt_document_path, "r", encoding='utf-8') as f:
                content = f.read()

            # Split content into parts with maximum 500 words each
            words = content.split()
            parts = []
            current_part = []
            word_count = 0

            for word in words:
                current_part.append(word)
                word_count += 1

                if word_count >= 500:
                    parts.append(' '.join(current_part))
                    current_part = []
                    word_count = 0

            if current_part:
                parts.append(' '.join(current_part))

            setting = SystemSetting.query.filter_by(
                setting_key='active_proofread_prompt_id').first()
            if not setting:
                raise ValueError("No active proofread prompt set")

            proofread_prompt = ProofreadPrompt.query.get(setting.setting_value)
            if not proofread_prompt:
                raise ValueError("Active proofread prompt not found")
            
            transcription.proofread_prompt = proofread_prompt.prompt
            db.session.commit()

            # Process all parts asynchronously
            processed_parts = asyncio.run(self.process_all_parts(parts, proofread_prompt.prompt))

            # Combine all processed parts
            combined_output = " ".join(processed_parts)

            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(combined_output)
            return True, output_path, None

        except Exception as e:
            return False, None, str(e)