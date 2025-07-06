import logging
from pathlib import Path
import random
import time
from typing import Optional

from flask import jsonify

from models import SystemSetting, TranscribePrompt, Transcription
import requests
import os
from database import db


class TranscriptionService:
    def __init__(self):
        self.transcribe_api_key = os.environ.get('TRANSCRIBE_API_KEY')
        self.transcribe_api_url = os.environ.get('TRANSCRIBE_API_URL')
        self.get_result_transcribe_api_url = os.environ.get(
            'GET_RESULT_TRANSCRIBE_API_URL')

    def transcribe(self, output_path: str, transcription: Transcription) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            self._call_inference_api(transcription)

            transcript_file = self._get_transcription_result(transcription.id)

            db.session.refresh(transcription)
            output_path = os.path.join(output_path,
                                       f"""{Path(transcription.audio_file_path).stem}.txt""")

            with open(output_path, 'wb') as f:
                f.write(transcript_file)

            return True, output_path, None

        except Exception as e:
            return False, None, str(e)

    def _call_inference_api(self, transcription: Transcription):
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

        # Check if file exists
        if not os.path.exists(transcription.audio_file_path):
            raise FileNotFoundError(
                f"Audio file not found: {transcription.audio_file_path}")

        headers = {"Authorization": f"Bearer {self.transcribe_api_key}"}
        data = {"transcription_id": str(transcription.id)}
        
        content_type_map = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.flac': 'audio/flac',
            '.ogg': 'audio/ogg',
            '.mp4': 'video/mp4',
            '.avi': 'video/avi',
            '.mov': 'video/quicktime'
        }
        # Determine content type based on file extension
        file_extension = os.path.splitext(
            transcription.audio_file_path)[1].lower()
        content_type = content_type_map.get(
            file_extension, 'application/octet-stream')

        try:
            with open(transcription.audio_file_path, "rb") as audio_file:
                files = {
                    "audio": (os.path.basename(transcription.audio_file_path), audio_file, content_type)
                }

                response = requests.post(
                    url=self.transcribe_api_url, headers=headers, data=data, files=files)

            response_data = response.json()

            if response.status_code == 200:
                logging.info(response_data.get('message'))
            elif response.status_code == 400:
                raise ValueError(
                    f"Inference API Error: {response_data.get('error')}")
            else:
                raise ValueError(
                    f"API Error {response.status_code}: {response.text}")

        except Exception as e:
            raise ValueError(f"Exception occurred during API call: {str(e)}")

    def _get_transcription_result(self, transcription_id: str):
        fetch_url = self.get_result_transcribe_api_url

        transcription = Transcription.query.get(transcription_id)
        while True:
            try:
                waiting_time = 10
                try:
                    time.sleep(waiting_time)
                except Exception as sleep_exc:
                    logging.warning(f"Sleep interrupted: {sleep_exc}. Waiting {waiting_time} seconds using busy-wait.")
                    start = time.time()
                    while time.time() - start < waiting_time:
                        pass

                db.session.refresh(transcription)

                if transcription.status == 'transcribing' or transcription.status == 'waiting':
                    print(
                        f"""Status: Transcription {transcription_id} is still in progress""")
                    continue
                elif transcription.status == 'waiting_for_proofreading':
                    response = requests.post(
                        fetch_url,
                        json={'transcription_id': str(transcription.id)},
                        headers={"Authorization": "Bearer " + self.transcribe_api_key})

                    if response.status_code == 200:
                        # Check if it's a "still in progress" message
                        if response.headers.get('Content-Type') == 'application/json':
                            result = response.json()
                            print(f"""Status: {result.get('message')}""")
                            continue
                        else:
                            # It's a file download - transcription is complete
                            return response.content
                    # elif response.status_code == 404 and response.headers.get('Content-Type') == 'application/json' and response.json().get('error') == 'Transcription file not found':
                    elif response.status_code == 404 and response.json().get('detail') == 'Transcription file not found':
                        print(
                            f"""Status: {response.json().get('error')}. Trying again in {waiting_time} seconds...""")
                        continue
                    else:
                        return f"""Error: {response.status_code} - {response.text}"""
                else:
                    return jsonify({"error": "Getting transcription failed"}), 400

            except Exception as e:
                return f"""Error occurred: {str(e)}"""
