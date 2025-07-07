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
        
        content_type = self._get_content_type(transcription.audio_file_path)

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

    def _get_content_type(file_path: str) -> str:
        """Returns the content type based on the file extension."""
        content_type_map = {
            # 🎵 Mainstream Audio Formats
            '.3gp': 'video/3gpp',             # Container with audio/video
            '.8svx': 'audio/x-8svx',           # Amiga 8-bit sampled voice
            '.aa': 'audio/audible',            # Audible audiobook
            '.aa3': 'audio/atrac3',            # Sony ATRAC3
            '.aac': 'audio/aac',               # Advanced Audio Coding
            '.aax': 'audio/aax',               # Audible enhanced audiobook
            '.aaxc': 'audio/aaxc',             # Audible encrypted
            '.ac3': 'audio/ac3',               # Dolby Digital
            '.act': 'audio/act',               # Low-bitrate voice recorder
            '.adts': 'audio/aac',              # ADTS AAC format
            '.adx': 'audio/adx',               # CRI ADX audio
            '.aif': 'audio/aiff',              # Audio Interchange File
            '.aifc': 'audio/x-aifc',           # Compressed AIFF
            '.aiff': 'audio/aiff',             # Audio Interchange File Format
            '.alac': 'audio/alac',             # Apple Lossless
            '.amr': 'audio/amr',               # Adaptive Multi-Rate
            '.ape': 'audio/ape',               # Monkey's Audio
            '.ast': 'audio/ast',               # Audio Stream
            '.au': 'audio/basic',              # Sun/NeXT audio
            '.avi': 'video/x-msvideo',         # Audio Video Interleave
            
            # 🎧 Lossless & High-Res Formats
            '.caf': 'audio/caf',               # Apple Core Audio
            '.cda': 'audio/cdda',              # CD Audio Track
            '.dff': 'audio/x-dff',             # DSD audio (SACD)
            '.dsf': 'audio/x-dsf',             # DSD Stream File
            '.dts': 'audio/vnd.dts',           # Digital Theater System
            '.dss': 'audio/dss',               # Digital Speech Standard
            '.flac': 'audio/flac',             # Free Lossless Audio Codec
            '.la': 'audio/la',                 # Lossless Audio
            '.lpac': 'audio/lpac',             # Lossless Predictive Audio
            '.ofr': 'audio/optimfrog',         # OptimFROG
            '.pac': 'audio/lpac',              # Lossless Predictive Audio
            '.pcm': 'audio/pcm',               # Raw PCM data
            '.shn': 'audio/shorten',           # Shorten compression
            '.tak': 'audio/x-tak',             # Tom's lossless Audio Kompressor
            '.tta': 'audio/tta',               # True Audio lossless
            '.wav': 'audio/wav',               # Waveform Audio
            '.wave': 'audio/wav',              # Waveform Audio
            '.wav64': 'audio/wave64',          # Sony Wave64
            '.wv': 'audio/wavpack',            # WavPack lossless
            
            # 🔉 Speech & Voice Formats
            '.gst': 'audio/gsm',               # GSM audio
            '.gsm': 'audio/gsm',               # Global System for Mobile
            '.iklax': 'audio/iklax',           # Iklax Multitrack
            '.qcp': 'audio/vnd.qcelp',         # Qualcomm PureVoice
            '.roq': 'audio/roq',               # Id Software audio
            '.sln': 'audio/wav',               # Signed Linear PCM
            '.vox': 'audio/vox',               # Dialogic ADPCM
            '.voxal': 'audio/voxal',           # Voxal Voice Changer
            
            # 🌐 Streaming & Web Formats
            '.m3u': 'audio/x-mpegurl',         # Playlist
            '.m3u8': 'application/vnd.apple.mpegURL', # HLS Playlist
            '.pls': 'audio/x-scpls',           # Playlist
            '.weba': 'audio/webm',             # WebM Audio
            '.webm': 'video/webm',             # Web Media
            
            # 🎮 Tracker & Module Formats
            '.it': 'audio/it',                 # Impulse Tracker
            '.mod': 'audio/mod',               # Amiga Module
            '.mtm': 'audio/mtm',               # MultiTracker
            '.ps': 'application/x-playstation-audio', # PlayStation Audio
            '.psf': 'audio/psf',               # PlayStation Sound Format
            '.s3m': 'audio/s3m',               # ScreamTracker 3
            '.umx': 'audio/umx',               # Unreal Music
            '.xm': 'audio/xm',                 # FastTracker 2
            
            # 📦 Container Formats
            '.cda': 'audio/cdda',              # CD Audio
            '.cue': 'application/x-cue',       # Cue sheet
            '.mat': 'audio/matlab',            # Matlab audio
            '.m2ts': 'video/mp2t',             # MPEG-2 Transport Stream
            '.m4a': 'audio/mp4',               # MPEG-4 Audio
            '.m4b': 'audio/m4b',               # Audiobook MP4
            '.m4p': 'audio/m4p',               # Protected AAC
            '.m4r': 'audio/mp4',               # iPhone ringtone
            '.mka': 'audio/x-matroska',        # Matroska Audio
            '.mkv': 'video/x-matroska',        # Matroska Video
            '.mov': 'video/quicktime',         # QuickTime
            '.mp2': 'audio/mpeg',              # MPEG-1 Layer II
            '.mp3': 'audio/mpeg',              # MPEG-1 Layer III
            '.mp4': 'video/mp4',               # MPEG-4
            '.mpa': 'audio/mpeg',              # MPEG-1 Audio
            '.mpc': 'audio/musepack',          # Musepack
            '.mpe': 'video/mpeg',              # MPEG-1
            '.mpeg': 'video/mpeg',             # MPEG-1/2
            '.mpg': 'video/mpeg',              # MPEG-1/2
            '.mts': 'video/mp2t',              # MPEG-2 Transport Stream
            '.oga': 'audio/ogg',               # Ogg Audio
            '.ogg': 'audio/ogg',               # Ogg Container
            '.opus': 'audio/opus',             # Opus Audio
            '.ra': 'audio/x-realaudio',        # RealAudio
            '.ram': 'audio/x-pn-realaudio',    # RealAudio Metadata
            '.rm': 'audio/x-pn-realaudio',     # RealMedia
            '.snd': 'audio/basic',             # Generic Sound
            '.spx': 'audio/ogg',               # Speex in Ogg
            '.ts': 'video/mp2t',               # MPEG-2 Transport Stream
            '.vorbis': 'audio/vorbis',         # Vorbis Audio
            '.voc': 'audio/x-voc',             # Creative Voice
            '.wma': 'audio/x-ms-wma',          # Windows Media Audio
            '.wmv': 'video/x-ms-wmv'           # Windows Media Video
        }
        
        file_extension = os.path.splitext(file_path)[1].lower()
        return content_type_map.get(file_extension, 'application/octet-stream')