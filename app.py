import streamlit as st
import random
import requests

# Load Airtable credentials from Streamlit Secrets
AIRTABLE_TOKEN = st.secrets["Airtable"]["token"]
BASE_ID = st.secrets["Airtable"]["base_id"]
TARGET_WORDS_TABLE = st.secrets["Airtable"]["target_words_table"]  # New secret for Target Words table name
SUBMISSIONS_TABLE = st.secrets["Airtable"]["table_name"]

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

    recording = st.file_uploader("Upload a Recording of Lilly's Attempt", type=["wav", "mp3", "m4a"])

    elicited_or_imitated = st.radio("Elicited or Imitated?", ("Elicited", "Imitated"))

    child_version = st.text_input("What did Lilly say?")

    outcome = st.selectbox("Outcome", ("Success", "Partial", "No Attempt"))

    comments = st.text_area("Comments/Notes")

    if st.button("Submit Attempt"):
        url = f"https://api.airtable.com/v0/{BASE_ID}/{SUBMISSIONS_TABLE}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_TOKEN}",
            "Content-Type": "application/json"
        }

        data = {
            "fields": {
                "Target Word": [word_to_record_id[selected_word]],
                "Elicited or Imitated": elicited_or_imitated,
                "Child's Version": child_version,
                "Outcome": outcome,
                "Comments": comments
            }
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code in [200, 201]:
            st.success("Speech attempt successfully logged!")
        else:
            st.error(f"Failed to log attempt. Status code: {response.status_code}")
            st.code(response.text)

    st.caption("Don't forget to record Lilly's lovely speech!")
else:
    st.info("Please select a word selection method from the sidebar.")
