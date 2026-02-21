import streamlit as st
import requests
import random
from collections import Counter

st.set_page_config(page_title="EuroMillions Generator", layout="centered")

st.title("🎰 EuroMillions Number Generator")
st.write("Generate 'smart' picks based on historical draws (just for fun!)")

@st.cache_data
def fetch_draws():
    url = "https://euromillions.api.pedromealha.dev/v1/draws"
    r = requests.get(url)
    data = r.json()
    return data

def generate_numbers(draws):
    numbers = []
    stars = []

    for d in draws:
        numbers.extend(d["numbers"])
        stars.extend(d["stars"])

    num_count = Counter(numbers)
    star_count = Counter(stars)

    # weighted picks
    main_nums = random.choices(list(num_count.keys()), weights=num_count.values(), k=5)
    lucky_stars = random.choices(list(star_count.keys()), weights=star_count.values(), k=2)

    return sorted(set(main_nums)), sorted(set(lucky_stars))


if st.button("Generate Numbers 🎯"):
    draws = fetch_draws()
    nums, stars = generate_numbers(draws)

    st.subheader("Your Numbers:")
    st.write(f"**{nums} + {stars}**")

    st.info("Remember: this is just for fun – lottery is random!")
