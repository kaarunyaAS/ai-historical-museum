// ======================================================
// AI HISTORICAL MUSEUM - FRONTEND JAVASCRIPT
// Whisper STT + Gemini Historical Chat
// ======================================================


// ------------------------------------------------------
// BACKEND URL
// ------------------------------------------------------

const API_URL = "http://127.0.0.1:8000";


// ------------------------------------------------------
// GLOBAL VARIABLES
// ------------------------------------------------------

let conversationHistory = [];

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;


// ------------------------------------------------------
// GET HTML ELEMENTS
// ------------------------------------------------------

const questionInput = document.getElementById("question");
const artifactSelect = document.getElementById("artifactSelect");
const chatBox = document.getElementById("chatBox");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const statusText = document.getElementById("status");


// ------------------------------------------------------
// STATUS
// ------------------------------------------------------

function setStatus(message) {
    statusText.textContent = message;
}


// ------------------------------------------------------
// ADD MESSAGE TO CHAT
// ------------------------------------------------------

function addMessage(sender, message) {

    const messageDiv = document.createElement("div");

    messageDiv.classList.add("message");


    if (sender === "user") {
        messageDiv.classList.add("visitor-message");
    } else {
        messageDiv.classList.add("ai-message");
    }


    const nameDiv = document.createElement("div");

    nameDiv.classList.add("message-name");


    if (sender === "user") {
        nameDiv.textContent = "👤 Visitor";
    } else {
        nameDiv.textContent = "🏛️ Historical AI";
    }


    const textDiv = document.createElement("div");

    textDiv.classList.add("message-text");

    textDiv.textContent = message;


    messageDiv.appendChild(nameDiv);
    messageDiv.appendChild(textDiv);

    chatBox.appendChild(messageDiv);


    // Scroll to bottom
    chatBox.scrollTop = chatBox.scrollHeight;
}


// ------------------------------------------------------
// SEND TEXT MESSAGE
// ------------------------------------------------------

async function sendMessage() {

    const question = questionInput.value.trim();


    // Don't send empty message
    if (!question) {
        return;
    }


    const artifactName = artifactSelect.value;


    // Show visitor message
    addMessage("user", question);


    // Clear input
    questionInput.value = "";


    setStatus("Historical AI is thinking...");


    // Disable only while request is running
    sendBtn.disabled = true;


    try {

        const response = await fetch(
            `${API_URL}/chat`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    artifact_name: artifactName,

                    visitor_question: question,

                    conversation_history: conversationHistory

                })
            }
        );


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail || "Chat request failed"
            );
        }


        // Show AI response
        addMessage(
            "ai",
            data.answer
        );


        // Save conversation
        conversationHistory.push({

            user: question,

            assistant: data.answer

        });


        setStatus("Ready");


    } catch (error) {

        console.error(
            "Chat Error:",
            error
        );


        addMessage(
            "ai",
            "I'm having trouble processing that right now. Please try again."
        );


        setStatus("Connection error");

    } finally {

        sendBtn.disabled = false;
    }
}


// ------------------------------------------------------
// ENTER KEY
// ------------------------------------------------------

questionInput.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            sendMessage();
        }
    }
);


// ------------------------------------------------------
// MICROPHONE TOGGLE
// ------------------------------------------------------

async function toggleRecording() {

    if (isRecording) {

        stopRecording();

    } else {

        await startRecording();

    }
}


// ------------------------------------------------------
// START RECORDING
// ------------------------------------------------------

async function startRecording() {

    if (isRecording) {
        return;
    }


    if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia
    ) {

        setStatus(
            "Microphone is not available in this browser."
        );

        return;
    }


    try {

        // Request microphone permission
        const stream =
            await navigator.mediaDevices.getUserMedia({
                audio: true
            });


        audioChunks = [];


        // Prefer WebM + Opus
        let mimeType = "audio/webm;codecs=opus";


        if (
            !MediaRecorder.isTypeSupported(
                "audio/webm;codecs=opus"
            )
        ) {

            if (
                MediaRecorder.isTypeSupported(
                    "audio/webm"
                )
            ) {

                mimeType = "audio/webm";

            } else if (
                MediaRecorder.isTypeSupported(
                    "audio/ogg;codecs=opus"
                )
            ) {

                mimeType = "audio/ogg;codecs=opus";

            } else {

                mimeType = "";
            }
        }


        // Create recorder
        if (mimeType) {

            mediaRecorder =
                new MediaRecorder(
                    stream,
                    {
                        mimeType: mimeType
                    }
                );

        } else {

            mediaRecorder =
                new MediaRecorder(stream);
        }


        // ----------------------------------------------
        // AUDIO DATA
        // ----------------------------------------------

        mediaRecorder.ondataavailable =
            function(event) {

                if (
                    event.data &&
                    event.data.size > 0
                ) {

                    audioChunks.push(
                        event.data
                    );
                }
            };


        // ----------------------------------------------
        // RECORDING START
        // ----------------------------------------------

        mediaRecorder.onstart =
            function() {

                isRecording = true;

                micBtn.textContent = "⏹️";

                setStatus(
                    "Listening... Speak now"
                );

                console.log(
                    "Recording started"
                );
            };


        // ----------------------------------------------
        // RECORDING STOP
        // ----------------------------------------------

        mediaRecorder.onstop =
            async function() {

                isRecording = false;

                micBtn.textContent = "🎤";

                setStatus(
                    "Processing speech..."
                );


                // Stop microphone
                stream
                    .getTracks()
                    .forEach(
                        track => track.stop()
                    );


                // Check audio
                if (
                    audioChunks.length === 0
                ) {

                    setStatus(
                        "No audio was recorded. Please try again."
                    );

                    return;
                }


                const actualMimeType =
                    mediaRecorder.mimeType ||
                    "audio/webm";


                const audioBlob =
                    new Blob(
                        audioChunks,
                        {
                            type: actualMimeType
                        }
                    );


                console.log(
                    "Audio size:",
                    audioBlob.size
                );


                console.log(
                    "Audio type:",
                    actualMimeType
                );


                if (audioBlob.size === 0) {

                    setStatus(
                        "Mic failed to record audio. Please try again."
                    );

                    return;
                }


                await sendAudioToWhisper(
                    audioBlob,
                    actualMimeType
                );
            };


        // ----------------------------------------------
        // RECORDING ERROR
        // ----------------------------------------------

        mediaRecorder.onerror =
            function(event) {

                console.error(
                    "MediaRecorder Error:",
                    event.error
                );


                isRecording = false;

                micBtn.textContent = "🎤";


                stream
                    .getTracks()
                    .forEach(
                        track => track.stop()
                    );


                setStatus(
                    "Mic failed to record audio. Please try again."
                );
            };


        // Start recording
        mediaRecorder.start(1000);


    } catch (error) {

        console.error(
            "Microphone Error:",
            error
        );


        isRecording = false;

        micBtn.textContent = "🎤";


        setStatus(
            "Microphone access failed."
        );


        alert(
            "Microphone access failed.\n\n" +
            "Please allow microphone permission and try again."
        );
    }
}


// ------------------------------------------------------
// STOP RECORDING
// ------------------------------------------------------

function stopRecording() {

    if (
        mediaRecorder &&
        mediaRecorder.state !== "inactive"
    ) {

        mediaRecorder.stop();

    } else {

        isRecording = false;

        micBtn.textContent = "🎤";

        setStatus("Ready");
    }
}


// ------------------------------------------------------
// SEND AUDIO TO WHISPER
// ------------------------------------------------------

async function sendAudioToWhisper(
    audioBlob,
    mimeType
) {

    if (
        !audioBlob ||
        audioBlob.size === 0
    ) {

        setStatus(
            "Mic failed to record audio. Please try again."
        );

        return;
    }


    const formData = new FormData();


    // Determine extension
    let filename = "visitor_audio.webm";


    if (
        mimeType &&
        mimeType.includes("ogg")
    ) {

        filename = "visitor_audio.ogg";
    }


    formData.append(
        "file",
        audioBlob,
        filename
    );


    try {

        setStatus(
            "Whisper is converting speech to text..."
        );


        const response =
            await fetch(
                `${API_URL}/transcribe`,
                {
                    method: "POST",
                    body: formData
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Speech transcription failed"
            );
        }


        console.log(
            "Whisper result:",
            data
        );


        // ----------------------------------------------
        // CHECK TRANSCRIPTION
        // ----------------------------------------------

        const text =
            (data.text || "").trim();


        if (!text) {

            setStatus(
                "No speech detected. Please speak again."
            );

            return;
        }


        console.log(
            "Detected language:",
            data.language
        );


        console.log(
            "Transcribed text:",
            text
        );


        // Put Whisper result into textbox
        questionInput.value = text;


        setStatus(
            `Detected language: ${data.language}`
        );


        // Automatically send to Gemini
        await sendMessage();


    } catch (error) {

        console.error(
            "Whisper Error:",
            error
        );


        setStatus(
            "Speech recognition failed."
        );


        alert(
            "Speech recognition failed.\n\n" +
            error.message
        );
    }
}


// ------------------------------------------------------
// CLEAR CHAT
// ------------------------------------------------------

function clearChat() {

    conversationHistory = [];


    chatBox.innerHTML = "";


    addMessage(
        "ai",
        "Hello! Select an artifact and ask me something about its history."
    );


    setStatus("Ready");
}