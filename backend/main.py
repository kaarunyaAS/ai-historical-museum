import logging
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.services.gemini_service import generate_historical_response
from backend.services.whisper_service import transcribe_audio


logger = logging.getLogger(__name__)


# ======================================================
# FASTAPI APP
# ======================================================

app = FastAPI(
    title="AI Historical Museum",
    description="Artifact-driven historical conversation system",
    version="1.0"
)


# ======================================================
# CORS
# ======================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================
# HISTORICAL DATA
# ======================================================

HISTORICAL_DATA = {

    "Tipu Sultan's Sword": """
Artifact Name:
Tipu Sultan's Sword

Historical Period:
18th Century

Associated Personality:
Tipu Sultan

Historical Context:
This sword is associated with Tipu Sultan,
the ruler of the Kingdom of Mysore.

Historical Significance:
The sword represents the military history
and heritage associated with the Mysore Kingdom
and the period of Tipu Sultan's rule.

Location:
Mysore, Karnataka, India.

Source:
Prototype historical dataset.
""",


    "Chola Bronze Nataraja": """
Artifact Name:
Chola Bronze Nataraja

Historical Period:
Chola Period

Associated Personality:
Associated with the religious and artistic
traditions of the Chola period.

Historical Context:
The Nataraja is a famous representation of Shiva
as the cosmic dancer and is strongly associated
with South Indian bronze sculpture traditions.

Historical Significance:
Chola bronze sculptures are important examples
of South Indian metalworking and religious art.

Location:
Tamil Nadu, India.

Source:
Prototype historical dataset.
""",


    "Lion Capital of Ashoka": """
Artifact Name:
Lion Capital of Ashoka

Historical Period:
Mauryan Period

Associated Personality:
Emperor Ashoka

Historical Context:
The Lion Capital is associated with Emperor Ashoka
and the Mauryan period of Indian history.

Historical Significance:
The sculpture is an important example of Mauryan
art and is associated with the historical legacy
of Ashoka.

Location:
Sarnath, India.

Source:
Prototype historical dataset.
"""
}


# ======================================================
# CHAT REQUEST MODEL
# ======================================================

class ChatRequest(BaseModel):

    artifact_name: str

    visitor_question: str

    conversation_history: list = Field(
        default_factory=list
    )


# ======================================================
# ROOT
# ======================================================

@app.get("/")
def home():

    return {
        "message": "AI Historical Museum API is running",
        "model": "gemini-3.5-flash-lite"
    }


# ======================================================
# GET ARTIFACT
# ======================================================

@app.get("/artifact/{artifact_name}")
def get_artifact(artifact_name: str):

    if artifact_name in HISTORICAL_DATA:

        return {
            "artifact_name": artifact_name,
            "historical_context":
                HISTORICAL_DATA[artifact_name]
        }


    return {
        "artifact_name": artifact_name,

        "historical_context":
            "Historical information is not available yet."
    }


# ======================================================
# CHAT API
# ======================================================

@app.post("/chat")
def chat(request: ChatRequest):

    try:

        artifact_name = request.artifact_name

        visitor_question = request.visitor_question

        conversation_history = request.conversation_history


        historical_context = HISTORICAL_DATA.get(
            artifact_name,

            "No historical information is available for this artifact."
        )


        answer = generate_historical_response(

            artifact_name=artifact_name,

            historical_context=historical_context,

            conversation_history=conversation_history,

            visitor_question=visitor_question
        )


        return {

            "artifact_name": artifact_name,

            "question": visitor_question,

            "answer": answer
        }


    except Exception as error:

        logger.exception(
            "Chat API error"
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "Unable to process the conversation. "
                "Please try again."
            )
        ) from error


# ======================================================
# WHISPER SPEECH-TO-TEXT
# ======================================================

@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...)
):

    extension = Path(
        file.filename or ""
    ).suffix.lower()


    if (
        not extension
        or len(extension) > 10
        or not extension[1:].isalnum()
    ):

        extension = ".webm"


    audio_path: str | None = None


    try:

        # ------------------------------------------------
        # READ AUDIO
        # ------------------------------------------------

        audio_data = await file.read()


        if not audio_data:

            raise HTTPException(
                status_code=400,

                detail=(
                    "The uploaded audio file is empty."
                )
            )


        # ------------------------------------------------
        # SAVE TEMPORARY AUDIO
        # ------------------------------------------------

        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False
        ) as audio_file:

            audio_file.write(audio_data)

            audio_path = audio_file.name


        logger.info(
            "Audio received: %s bytes, format=%s",
            len(audio_data),
            extension
        )


        # ------------------------------------------------
        # WHISPER
        # ------------------------------------------------

        try:

            result = transcribe_audio(
                audio_path
            )


        except RuntimeError as error:

            error_message = str(error)


            logger.exception(
                "Whisper runtime error: %s",
                error_message
            )


            if (
                error_message.startswith(
                    "Failed to load audio:"
                )
                or "ffmpeg" in error_message.lower()
                or "decode" in error_message.lower()
            ):

                raise HTTPException(

                    status_code=400,

                    detail=(
                        "The uploaded audio could not be decoded. "
                        "Please check the microphone recording "
                        "and make sure FFmpeg is installed."
                    )

                ) from error


            raise HTTPException(

                status_code=503,

                detail=(
                    "Speech transcription is currently unavailable. "
                    "Please check Whisper, PyTorch and FFmpeg."
                )

            ) from error


        except subprocess.CalledProcessError as error:

            logger.exception(
                "FFmpeg/audio decoding error"
            )


            raise HTTPException(

                status_code=400,

                detail=(
                    "The recorded audio could not be processed. "
                    "Please try recording again."
                )

            ) from error


        except (ImportError, OSError) as error:

            logger.exception(
                "Whisper dependency error"
            )


            raise HTTPException(

                status_code=503,

                detail=(
                    "Speech transcription is unavailable. "
                    "Please check that Whisper, PyTorch "
                    "and FFmpeg are installed correctly."
                )

            ) from error


        except Exception as error:

            logger.exception(
                "Unexpected Whisper error"
            )


            raise HTTPException(

                status_code=503,

                detail=(
                    "Speech recognition failed. "
                    "Please try again."
                )

            ) from error


        # ------------------------------------------------
        # GET RESULT
        # ------------------------------------------------

        text = result.get(
            "text",
            ""
        ).strip()


        language = result.get(
            "language",
            "unknown"
        )


        if not text:

            return {

                "success": False,

                "text": "",

                "language": language,

                "message":
                    "No speech was detected."
            }


        logger.info(
            "Whisper transcription successful: "
            "language=%s, text=%s",
            language,
            text
        )


        return {

            "success": True,

            "text": text,

            "language": language
        }


    finally:

        # ------------------------------------------------
        # DELETE TEMP FILE
        # ------------------------------------------------

        if audio_path is not None:

            try:

                Path(
                    audio_path
                ).unlink(
                    missing_ok=True
                )

            except Exception as error:

                logger.warning(
                    "Could not delete temporary audio file: %s",
                    error
                )


# ======================================================
# FRONTEND
# ======================================================

frontend_path = (
    Path(__file__).resolve().parent.parent
    / "frontend"
)


app.mount(
    "/app",
    StaticFiles(
        directory=frontend_path,
        html=True
    ),
    name="frontend"
)