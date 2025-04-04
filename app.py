import streamlit as st
import random
import requests
import os
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av
import tempfile

# Airtable credentials from Environment Variables
AIRTABLE_TOKEN = os.environ["AIRTABLE_TOKEN"]
BASE_ID = os.environ["BASE_ID"]
TARGET_WORDS_TABLE = os.environ["TARGET_WORDS_TABLE"]
SUBMISSIONS_TABLE = os.environ["SUBMISSIONS_TABLE"]

# Fetch Target Words dynamically from Airtable
def fetch_target_words():
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TARGET_WORDS_TABLE}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    word_list = []
    word_to_record_id = {}

    if response.status_code == 200:
        records = response.json()["records"]
        for record in records:
            fields = record.get("fields", {})
            word = fields.get("Word")
            category = fields.get("Sound Class", "Other")
            if word:
                word_list.append({"word": word, "category": category})
                word_to_record_id[word] = record["id"]
    else:
        st.error("Failed to fetch Target Words from Airtable.")

    return word_list, word_to_record_id

word_list, word_to_record_id = fetch_target_words()

# Extract categories
temp_categories = set()
for w in word_list:
    if w["category"]:
        temp_categories.add(w["category"])
categories = sorted(list(temp_categories))

# Streamlit App
st.title("Lilly's Speech Tracker")

st.sidebar.header("Word Selection Method")
selection_mode = st.sidebar.radio("How would you like to select a word?", ("Random", "By Category", "Manual"))

selected_word = None

if selection_mode == "Random" and word_list:
    selected_word = random.choice(word_list)["word"]
elif selection_mode == "By Category" and categories:
    category = st.sidebar.selectbox("Choose a category", categories)
    filtered_words = [w["word"] for w in word_list if w["category"] == category]
    if filtered_words:
        selected_word = random.choice(filtered_words)
elif selection_mode == "Manual" and word_list:
    selected_word = st.sidebar.selectbox("Select a word", sorted([w["word"] for w in word_list]))

if selected_word:
    st.header(f"Selected Word: {selected_word}")

    st.write("### Record Audio")

    # WebRTC audio recording
    class AudioProcessor(AudioProcessorBase):
        def __init__(self):
            self.recorded_frames = []

        def recv_audio(self, frame: av.AudioFrame) -> av.AudioFrame:
            self.recorded_frames.append(frame)
            return frame

    ctx = webrtc_streamer(
        key="audio",
        audio_receiver_size=1024,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True
    )

    elicited_or_imitated = st.radio("Elicited or Imitated?", ("Elicited", "Imitated"))

    child_version = st.text_input("What did Lilly say?")

    outcome = st.selectbox("Outcome", ("Success", "Partial", "No Attempt"))

    comments = st.text_area("Comments/Notes")

    if st.button("Submit Attempt"):
        audio_url = None

        if ctx.state.audio_processor and ctx.state.audio_processor.recorded_frames:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
                container = av.open(tmpfile.name, mode='w', format='wav')
                stream = container.add_stream("pcm_s16le")

                for frame in ctx.state.audio_processor.recorded_frames:
                    frame.pts = None
                    frame.time_base = None
                    container.mux(frame)
                container.close()

                # Upload to Airtable
                with open(tmpfile.name, "rb") as f:
                    files = {"file": ("recording.wav", f, "audio/wav")}
                    upload_response = requests.post(
                        f"https://api.airtable.com/v0/{BASE_ID}/{SUBMISSIONS_TABLE}",
                        headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"},
                        files=files
                    )

        # Submit form fields to Airtable
        url = f"https://api.airtable.com/v0/{BASE_ID}/{SUBMISSIONS_TABLE}"
        headers = {
            "Authorization": f"Bearer {AIRTABLE_TOKEN}",
            "Content-Type": "application/json"
        }

        fields_data = {
            "Target Word": [word_to_record_id[selected_word]],
            "Elicited or Imitated": elicited_or_imitated,
            "Child's Version": child_version,
            "Outcome": outcome,
            "Comments": comments
        }

        data = {"fields": fields_data}

        response = requests.post(url, headers=headers, json=data)

        if response.status_code in [200, 201]:
            st.success("Speech attempt successfully logged with recording!")
        else:
            st.error(f"Failed to log attempt. Status code: {response.status_code}")
            st.code(response.text)

    st.caption("Don't forget to record Lilly's lovely speech!")
else:
    st.info("Please select a word selection method from the sidebar.")
