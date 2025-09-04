import subprocess
import sys

def run_streamlit():
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit: {e}")
    except KeyboardInterrupt:
        print("Streamlit app stopped by user")

if __name__ == "__main__":
    run_streamlit()
