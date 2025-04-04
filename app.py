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

# Set up session state
if 'selected_word' not in st.session_state:
    st.session_state.selected_word = None
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None

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

if st.session_state.selected_word is None:
    if selection_mode == "Random" and word_list:
        st.session_state.selected_word = random.choice(word_list)["word"]
    elif selection_mode == "By Category" and categories:
        category = st.sidebar.selectbox("Choose a category", categories)
        filtered_words = [w["word"] for w in word_list if w["category"] == category]
        if filtered_words:
            st.session_state.selected_word = random.choice(filtered_words)
    elif selection_mode == "Manual" and word_list:
        st.session_state.selected_word = st.sidebar.selectbox("Select a word", sorted([w["word"] for w in word_list]))

selected_word = st.session_state.selected_word

if selected_word:
    with st.container():
        st.success(f"🎯 Word to practice: **{selected_word}**")

    st.write("### 🎙️ Record Audio")

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

    if ctx.state.playing:
        st.success("🎙️ Recording in progress...")
    elif ctx.state.recording:
        st.info("🔴 Connecting to microphone...")
    else:
        st.warning("🎙️ Click allow and start speaking to record!")

    st.write("---")

    col1, col2 = st.columns(2)

    with col1:
        elicited_or_imitated = st.radio("Elicited or Imitated?", ("Elicited", "Imitated"))

    with col2:
        outcome = st.selectbox("Outcome", ("Success", "Partial", "No Attempt"))

    child_version = st.text_input("🗣️ What did Lilly say?")

    comments = st.text_area("📝 Comments/Notes")

    if ctx.state and hasattr(ctx.state, 'audio_processor') and ctx.state.audio_processor and ctx.state.audio_processor.recorded_frames:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            container = av.open(tmpfile.name, mode='w', format='wav')
            stream = container.add_stream("pcm_s16le")

            for frame in ctx.state.audio_processor.recorded_frames:
                frame.pts = None
                frame.time_base = None
                container.mux(frame)
            container.close()

            st.session_state.audio_file_path = tmpfile.name

    if st.session_state.audio_file_path:
        st.audio(st.session_state.audio_file_path, format='audio/wav')

    if st.button("🚀 Submit Attempt", use_container_width=True):
        if st.session_state.audio_file_path:
            with st.spinner("Saving your speech attempt..."):
                # Upload to Airtable
                with open(st.session_state.audio_file_path, "rb") as f:
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
                    st.success("✅ Speech attempt successfully logged with recording!")
                    st.session_state.selected_word = None
                    st.session_state.audio_file_path = None
                else:
                    st.error(f"Failed to log attempt. Status code: {response.status_code}")
                    st.code(response.text)
        else:
            st.warning("⚠️ Please record audio before submitting!")

    st.caption("🎯 Ready to record Lilly's lovely speech!")
else:
    st.info("Please select a word selection method from the sidebar.")
