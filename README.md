# Voice Recorder for Raspberry Pi

A voice recording web application built with Streamlit for Raspberry Pi (320x480) that captures audio through the browser and automatically uploads recordings to AWS S3.

## Features

- Browser-based voice recording
- Portrait mode optimization (320x480 display)
- Direct upload to AWS S3
- Automatic file naming with timestamps
- Pre-signed URL generation for secure file access
- Responsive touch-friendly interface
- Error handling and user feedback

## Prerequisites

- Raspberry Pi (tested on Raspberry Pi 4)
- Python 3.7+
- AWS Identity Center (SSO) Access
- Microphone connected to Raspberry Pi
- Internet connection

## Hardware Setup

1. Connect your microphone to the Raspberry Pi
2. Set up your 320x480 display in portrait mode
3. Ensure your Raspberry Pi is connected to the internet

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/raspberry-pi-voice-recorder.git
cd raspberry-pi-voice-recorder
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## AWS Configuration

1. Configure AWS CLI with SSO:
```bash
aws configure sso
# Follow the prompts to set up your SSO connection
```

2. Login to AWS SSO:
```bash
aws sso login
```

3. Verify your credentials are working:
```bash
aws sts get-caller-identity
```

4. Create a `.streamlit` directory and `secrets.toml` file:
```bash
mkdir .streamlit
```

5. Add your S3 bucket name to `.streamlit/secrets.toml`:
```toml
BUCKET_NAME = "your-bucket-name"
```

6. Ensure your AWS S3 bucket has appropriate permissions in its bucket policy:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        }
    ]
}
```

## Running the Application

1. Ensure you have an active AWS SSO session:
```bash
aws sso login
```

2. Start the Streamlit server:
```bash
streamlit run app.py
```

3. Access the application in your browser at:
```
http://localhost:8501
```

For Raspberry Pi access from other devices on your network, use:
```
http://[your-pi-ip]:8501
```

## Usage

1. Click the microphone button to start recording
2. Speak into your microphone
3. Click again to stop recording
4. The recording will automatically upload to your S3 bucket
5. A pre-signed URL will be generated for accessing the recording

## File Structure

```
.
├── .streamlit/
│   └── secrets.toml
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Troubleshooting

### Common Issues:

1. **Microphone not detected:**
   - Check if your microphone is properly connected
   - Verify microphone permissions in your browser
   - Run `arecord -l` to list available recording devices

2. **AWS Upload Errors:**
   - Verify your AWS SSO session is active (`aws sts get-caller-identity`)
   - Check S3 bucket permissions
   - Ensure internet connectivity

3. **Display Issues:**
   - Verify your display resolution settings
   - Check if X server is running in portrait mode


## Security Considerations

- Keep your AWS SSO credentials secure
- Regularly monitor your S3 bucket for unusual activity
- Review AWS IAM permissions regularly
- Consider implementing additional authentication


## License

This project is licensed under the MIT License - see the LICENSE file for details.


