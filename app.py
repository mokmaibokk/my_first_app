import streamlit as st

st.title("My First Streamlit App")
name = st.text_input("Enter your name")
b = st.button("Click Me")
if b:
    st.write(f"Hello, {name}!")
