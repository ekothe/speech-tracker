import streamlit as st
import random
import requests

# Load Airtable credentials from Streamlit Secrets
AIRTABLE_TOKEN = st.secrets["Airtable"]["token"]
BASE_ID = st.secrets["Airtable"]["base_id"]
TABLE_NAME = st.secrets["Airtable"]["table_name"]

# Word to Record ID mapping
word_to_record_id = {
    "pig": "recCRXiLOgFkl1kqr",
    "ball": "recQF2QcxHd1qytcE",
    "cup": "recNlsLOZgbisgBkN",
    "dog": "recRtwdBvNTAR9zZg",
    "cat": "recwotmBqv6EznIjz",
    "go": "recixx9q5tYxW8x0D",
    "happy": "reczz2JDNtkJD0CA2",
    "baby": "recFAvAK12XZWDsOh",
    "tiger": "recxMD5Zm3lzyNDUX",
    "bucket": "recCqTnD3PWRl6D8e",
    "mum": "rec67ZL9K4eVeyLMz",
    "nose": "recU4Rn8HZiGPoDcC",
    "jam": "recidStqZqkLZ2KQQ",
    "fish": "rec2Rz2gkDZDRMyok",
    "van": "rec83pqkZbHG1pEvm",
    "sun": "recN2RtS3dMYjWcT5",
    "zoo": "recEomjztOrr2RcvI",
    "shoe": "recGS7X1DczP9Pywu",
    "brush": "recZAfkOUf6WqMvoM",
    "chair": "recz6Hc0HLVGcM9Bq",
    "water": "recjUZF99cnQMTll1",
    "yellow": "rec24IEuD5gMXkpa4"
}

# Word list with categories
word_list = [
    {"word": "pig", "category": "Stops (P/B)"},
    {"word": "ball", "category": "Stops (P/B)"},
    {"word": "cup", "category": "Stops (P/K)"},
    {"word": "dog", "category": "Stops (T/D)"},
    {"word": "cat", "category": "Stops (T/D)"},
    {"word": "go", "category": "Velars (K/G)"},
    {"word": "happy", "category": "Other"},
    {"word": "baby", "category": "Stops (P/B)"},
    {"word": "tiger", "category": "Other"},
    {"word": "bucket", "category": "Other"},
    {"word": "mum", "category": "Nasals (M/N)"},
    {"word": "nose", "category": "Nasals (M/N)"},
    {"word": "jam", "category": "Affricates"},
    {"word": "fish", "category": "Fricatives (F/V)"},
    {"word": "van", "category": "Fricatives (F/V)"},
    {"word": "sun", "category": "Fricatives (S/Z)"},
    {"word": "zoo", "category": "Fricatives (S/Z)"},
    {"word": "shoe", "category": "Fricatives (SH)"},
    {"word": "brush", "category": "Fricatives (S/Z)"},
    {"word": "chair", "category": "Affricates"},
    {"word": "water", "category": "Glides (W/Y)"},
    {"word": "yellow", "category": "Glides (W/Y)"},
]

# Extract categories
categories = sorted(list(set([w["category"] for w in word_list])))

# Streamlit App
st.title("Lilly's Speech Tracker")

st.sidebar.header("Word Selection Method")
selection_mode = st.sidebar.radio("How would you like to select a word?", ("Random", "By Category", "Manual"))

selected_word = None

if selection_mode == "Random":
    selected_word = random.choice(word_list)["word"]
elif selection_mode == "By Category":
    category = st.sidebar.selectbox("Choose a category", categories)
    filtered_words = [w["word"] for w in word_list if w["category"] == category]
    if filtered_words:
        selected_word = random.choice(filtered_words)
elif selection_mode == "Manual":
    selected_word = st.sidebar.selectbox("Select a word", sorted([w["word"] for w in word_list]))

if selected_word:
    st.header(f"Selected Word: {selected_word}")

    recording = st.file_uploader("Upload a Recording of Lilly's Attempt", type=["wav", "mp3", "m4a"])

    elicited_or_imitated = st.radio("Elicited or Imitated?", ("Elicited", "Imitated"))

    child_version = st.text_input("What did Lilly say?")

    outcome = st.selectbox("Outcome", ("Success", "Partial", "No Attempt"))

    comments = st.text_area("Comments/Notes")

    if st.button("Submit Attempt"):
        url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"

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
