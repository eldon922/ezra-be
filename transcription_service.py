import logging
import time
from typing import Optional
from models import SystemSetting, TranscribePrompt, Transcription
import requests
import os
from database import db


class TranscriptionService:
    def __init__(self):
        self.api_key = os.environ.get('TRANSCRIBE_API_KEY')
        self.url = os.environ.get('TRANSCRIBE_API_URL')

    def transcribe(self, file_path: str, output_path: str, transcription: Transcription) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            self._call_inference_api(file_path, transcription)

            transcript_file = self._get_transcription_result(transcription)

            with open(output_path, 'wb') as f:
                f.write(transcript_file)

            return True, output_path, None

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return False, None, str(e)

    def _call_inference_api(self, file_path: str, transcription: Transcription):
        active_transcribe_prompt_setting = SystemSetting.query.filter_by(
            setting_key='active_transcribe_prompt_id').first()
        if not active_transcribe_prompt_setting:
            raise ValueError("No active transcribe prompt set")

        transcribe_prompt = TranscribePrompt.query.get(
            active_transcribe_prompt_setting.setting_value)
        if not transcribe_prompt:
            raise ValueError("Active transcribe prompt not found")
        
        transcription.transcribe_prompt = transcribe_prompt.prompt
        db.session.commit()

        # Prepare the data and files for the POST request
        data = {
            'transcription_id': transcription.id
        }
        files = {
            'audio': open(file_path, 'rb')
        }

        # Add the API key to the headers
        headers = {
            'x-api-key': self.api_key
        }
        inference_url = f"{self.url}/process"

        # Make the POST request to the Flask API
        response = requests.post(
            inference_url, data=data, files=files, headers=headers)

        if response.status_code == 200:
            logging.info(response.json().get(
                'message', 'Something unexpected happened'))
        else:
            logging.error(transcript_result = response.json().get(
                'error', 'Error in transcription request'))
            
    def _get_transcription_result(self, transcription: Transcription):
        # Construct the full URL
        fetch_url = f"{self.url}/gettranscriptionresult/{transcription.id}"
        
        # Set up headers with API key
        headers = {
            "x-api-key": self.api_key
        }
        
        while True:  # Keep checking until complete
            try:
                # Wait before checking
                time.sleep(10)  # Wait 10 seconds between checks

                response = requests.get(fetch_url, headers=headers)
                
                if response.status_code == 200:
                    # Check if it's a "still in progress" message
                    if response.headers.get('Content-Type') == 'application/json':
                        result = response.json()
                        print(f"Status: {result.get('message')}")
                        continue
                    else:
                        # It's a file download - transcription is complete
                        return response.content
                else:
                    return f"Error: {response.status_code} - {response.text}"
                    
            except Exception as e:
                return f"Error occurred: {str(e)}"