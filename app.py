import streamlit as st
import sounddevice as sd
import numpy as np
import wave
import boto3
from datetime import datetime
import pytz
import os
import time
import logging
from pathlib import Path

# Set up logging to write to a file in the same directory as the script
log_file = Path(__file__).parent / "streamlit.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure page layout for portrait mode (320x480)
st.set_page_config(
    page_title="Voice Recorder",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS to optimize for portrait mode
st.markdown("""
    <style>
        .stButton > button {
            width: 280px;
            height: 80px;
            font-size: 24px;
            margin: 10px auto;
            display: block;
        }
        .stMarkdown {
            text-align: center;
        }
        div[data-testid="stVerticalBlock"] {
            padding-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state variables
if 'audio_data' not in st.session_state:
    st.session_state['audio_data'] = []
if 'recording' not in st.session_state:
    st.session_state['recording'] = False
if 'audio_recorder' not in st.session_state:
    st.session_state['audio_recorder'] = None
if 'error_message' not in st.session_state:
    st.session_state['error_message'] = None
if 'last_recording_status' not in st.session_state:
    st.session_state['last_recording_status'] = None

# Get S3 bucket name from secrets
BUCKET_NAME = st.secrets.get("BUCKET_NAME", "")
S3_FOLDER = "source"

class AudioRecorder:
    def __init__(self):
        self.audio_data = []
        self.recording = False
        self.stream = None
        logger.info("AudioRecorder initialized")

    def callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Stream status: {status}")
        if self.recording:
            self.audio_data.extend(indata.copy())

    def start(self):
        logger.info("Starting recording")
        self.audio_data = []
        self.recording = True
        self.stream = sd.InputStream(
            channels=1,
            samplerate=44100,
            callback=self.callback
        )
        self.stream.start()
        logger.info("Recording started successfully")

    def stop(self):
        logger.info("Stopping recording")
        if self.stream:
            self.recording = False
            self.stream.stop()
            self.stream.close()
            logger.info(f"Recording stopped. Captured {len(self.audio_data)} samples")
            return np.array(self.audio_data)
        logger.warning("No stream to stop")
        return np.array([])

def save_audio(audio_data, filename):
    """Save recorded audio to a WAV file"""
    logger.info(f"Attempting to save audio to {filename}")
    if len(audio_data) == 0:
        logger.error("No audio data to save")
        return False
        
    try:
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes((audio_data * np.iinfo(np.int16).max).astype(np.int16))
        logger.info(f"Audio saved successfully to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving audio: {str(e)}")
        raise

def upload_to_s3(filename):
    """Upload file to S3 using default credentials from AWS CLI session"""
    logger.info(f"Attempting to upload {filename} to S3")
    try:
        # Use default session credentials from AWS SSO
        s3_client = boto3.client('s3')
        
        timestamp = datetime.now(pytz.UTC).strftime('%Y%m%d_%H%M%S')
        object_key = f"{S3_FOLDER}/{timestamp}_{os.path.basename(filename)}"
        
        logger.info(f"Uploading to S3 bucket: {BUCKET_NAME}, key: {object_key}")
        with open(filename, 'rb') as file:
            s3_client.upload_fileobj(file, BUCKET_NAME, object_key)
        
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': object_key},
            ExpiresIn=3600
        )
        logger.info("Upload successful, presigned URL generated")
        return presigned_url
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise

# Display any persistent error message
if st.session_state['error_message']:
    st.error(st.session_state['error_message'])
    st.session_state['error_message'] = None

# Display last recording status
if st.session_state['last_recording_status']:
    st.info(st.session_state['last_recording_status'])
    st.session_state['last_recording_status'] = None

# Main app layout
st.title("Voice Recorder")

# Debug information
if st.checkbox("Show Debug Info"):
    st.write("Recording State:", st.session_state['recording'])
    if st.session_state.get('audio_recorder'):
        st.write("Audio Data Length:", len(st.session_state['audio_recorder'].audio_data))

# Recording button
if st.button("🎤 " + ("Stop Recording" if st.session_state['recording'] else "Start Recording")):
    if not st.session_state['recording']:
        # Start recording
        try:
            st.session_state['audio_recorder'] = AudioRecorder()
            st.session_state['audio_recorder'].start()
            st.session_state['recording'] = True
            st.session_state['last_recording_status'] = "Recording started..."
            st.experimental_rerun()
        except Exception as e:
            logger.error(f"Error starting recording: {str(e)}")
            st.session_state['error_message'] = f"Failed to start recording: {str(e)}"
            st.experimental_rerun()
    else:
        # Stop recording
        try:
            if st.session_state['audio_recorder']:
                audio_data = st.session_state['audio_recorder'].stop()
                st.session_state['recording'] = False
                
                if len(audio_data) > 0:
                    # Save the recording
                    filename = "temp_recording.wav"
                    try:
                        save_audio(audio_data, filename)
                        st.session_state['last_recording_status'] = "Audio saved successfully"
                        
                        # Upload to S3
                        try:
                            presigned_url = upload_to_s3(filename)
                            if presigned_url:
                                st.session_state['last_recording_status'] = "Recording uploaded successfully!"
                                st.session_state['download_url'] = presigned_url
                        except Exception as e:
                            logger.error(f"S3 upload failed: {str(e)}")
                            st.session_state['error_message'] = f"Failed to upload to S3: {str(e)}"
                        
                        # Clean up
                        os.remove(filename)
                        
                    except Exception as e:
                        logger.error(f"Error processing recording: {str(e)}")
                        st.session_state['error_message'] = f"Error processing recording: {str(e)}"
                else:
                    logger.warning("No audio data recorded")
                    st.session_state['error_message'] = "No audio data recorded. Please check your microphone settings."
        except Exception as e:
            logger.error(f"Error stopping recording: {str(e)}")
            st.session_state['error_message'] = f"Error stopping recording: {str(e)}"
        finally:
            st.experimental_rerun()

# Show recording status
if st.session_state['recording']:
    st.markdown("### 🔴 Recording in progress...")
    placeholder = st.empty()
    while st.session_state['recording']:
        placeholder.text("Recording... " + "." * (int(time.time()) % 4))
        time.sleep(0.1)

# Display download URL if available
if 'download_url' in st.session_state and st.session_state['download_url']:
    st.markdown(f"Access your recording [here]({st.session_state['download_url']})")
    st.session_state['download_url'] = None

# Show system information
if st.checkbox("Show System Info"):
    try:
        devices = sd.query_devices()
        st.write("Available Audio Devices:", devices)
        default_device = sd.query_devices(kind='input')
        st.write("Default Input Device:", default_device)
    except Exception as e:
        logger.error(f"Error querying audio devices: {str(e)}")
        st.error(f"Error querying audio devices: {str(e)}")

# Show log viewer
if st.checkbox("Show Logs"):
    try:
        if log_file.exists():
            with open(log_file, 'r') as log_file_handle:
                log_contents = log_file_handle.read()
                if log_contents:
                    st.code(log_contents)
                else:
                    st.info("Log file is empty")
        else:
            st.info("No logs generated yet")
    except Exception as e:
        st.error(f"Error reading log file: {str(e)}")

st.markdown("---")
st.markdown("Click the button above to start/stop recording")
