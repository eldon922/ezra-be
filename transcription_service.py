import logging
import time
from typing import Optional

from models import SystemSetting, TranscribePrompt, Transcription
import requests
import os
from database import db


class TranscriptionService:
    def __init__(self):
        self.transcribe_api_key = os.environ.get('TRANSCRIBE_API_KEY')
        self.transcribe_api_url = os.environ.get('TRANSCRIBE_API_URL')
        self.tensordock_api_url = os.environ.get('TENSORDOCK_API_URL')
        self.tensordock_api_key = os.environ.get('TENSORDOCK_API_KEY')
        self.tensordock_api_token = os.environ.get('TENSORDOCK_API_TOKEN')
        self.tensordock_vm_uuid = os.environ.get('TENSORDOCK_VM_UUID')

    def transcribe(self, output_path: str, transcription: Transcription) -> tuple[bool, str, Optional[str]]:
        """Returns (success, output_path, error_message)"""
        try:
            self._call_inference_api(transcription)

            transcript_file = self._get_transcription_result(transcription.id)

            with open(output_path, 'wb') as f:
                f.write(transcript_file)

            return True, output_path, None

        except Exception as e:
            logging.error(f"""An error occurred: {e}""")
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

        self._start_vm()

        while True:
            # Make the POST request to the Flask API
            try:
                response = requests.post(
                    f"""{self.transcribe_api_url}/process""",
                    data={'transcription_id': transcription.id},
                    files={'audio': open(transcription.audio_file_path, 'rb')},
                    headers={'x-api-key': self.transcribe_api_key}
                )
            except Exception as e:
                logging.warning(f"""Error occurred: {
                                str(e)}. Retrying in 60 seconds...""")
                time.sleep(60)
                continue

            # Parse response
            response_data = response.json()

            # Check the response status code
            if response.status_code == 200:
                # If request was successful, break out of loop
                logging.info(response_data.get('message'))
                break
            elif response.status_code == 400:
                # If there's an error with the request, raise it
                raise ValueError(f"""Inference API Error: {
                                 response_data.get('error')}""")
            else:
                # For other status codes, wait and retry
                logging.warning(f"""Received status code {
                                response.status_code}. Retrying in 60 seconds...""")
                time.sleep(60)
                continue

    def _start_vm(self):
        try:
            # Prepare request to TensorDock API
            url = f"""{self.tensordock_api_url}/start/single"""
            payload = {
                'api_key': self.tensordock_api_key,
                'api_token': self.tensordock_api_token,
                'server': self.tensordock_vm_uuid
            }

            while (True):
                # Make request to TensorDock
                response = requests.post(url, data=payload)
                response.raise_for_status()

                # Parse response
                response_data = response.json()

                # Handle specific response cases
                if response_data.get('success') is True:
                    time.sleep(60)  # Wait for VM to fully start up
                    logging.info("VM started successfully")
                    return
                elif response_data.get('error') == "Machine is running, therefore it cannot be started":
                    logging.info("VM is already running")
                    return
                else:
                    logging.info(
                        f"""Failed to start VM. Retrying in 60 seconds...""")
                    time.sleep(60)
                    continue

        except requests.exceptions.RequestException as e:
            logging.error(
                f"""Failed to communicate with TensorDock API during starting VM. HTTP 500 ({str(e)})""")

    def stop_vm(self):
        try:
            # Check if there are any other running transcriptions
            running_transcriptions = Transcription.query.filter(
                Transcription.status.in_(
                    ['uploading', 'waiting', 'transcribing', 'waiting_for_proofreading'])
            ).count()
            if running_transcriptions > 0:
                logging.info(
                    f"""Found {running_transcriptions} running transcriptions. Keeping VM running.""")
                return

            # Prepare request to TensorDock API
            url = f"""{self.tensordock_api_url}/stop/single"""
            payload = {
                'api_key': self.tensordock_api_key,
                'api_token': self.tensordock_api_token,
                'server': self.tensordock_vm_uuid,
                'disassociate_resources': True
            }

            while (True):
                # Make request to TensorDock
                response = requests.post(url, data=payload)
                response.raise_for_status()

                # Parse response
                response_data = response.json()

                if response_data.get('success') is True:
                    logging.info("VM stopped successfully")
                    return
                elif response_data.get('error') == "Machine is stoppeddisassociated, therefore it cannot be stopped":
                    logging.info("VM is already stopped")
                    return
                else:
                    logging.info(
                        f"""Failed to stop VM. Retrying in 60 seconds...""")
                    time.sleep(60)
                    continue

        except requests.exceptions.RequestException as e:
            logging.error(
                f"""Failed to communicate with TensorDock API during stopping VM. HTTP 500 ({str(e)})""")

    def _get_transcription_result(self, transcription_id: str):
        fetch_url = f"""{
            self.transcribe_api_url}/gettranscriptionresult/{transcription_id}"""

        while True:
            try:
                time.sleep(10)  # Wait 10 seconds between checks

                response = requests.get(
                    fetch_url, headers={"x-api-key": self.transcribe_api_key})

                if response.status_code == 200:
                    # Check if it's a "still in progress" message
                    if response.headers.get('Content-Type') == 'application/json':
                        result = response.json()
                        print(f"""Status: {result.get('message')}""")
                        continue
                    else:
                        # It's a file download - transcription is complete
                        return response.content
                else:
                    return f"""Error: {response.status_code} - {response.text}"""

            except Exception as e:
                return f"""Error occurred: {str(e)}"""
