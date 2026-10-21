import os
import streamlit as st

from ui import render_monitoramento

st.write(f"**PID:** {os.getpid()}")
st.write(f"**CWD:** {os.getcwd()}")
st.write(f"**Arquivo:** {__file__}")
render_monitoramento()
