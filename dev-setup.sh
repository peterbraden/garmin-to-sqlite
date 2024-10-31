# Create a virtual environment
python3.12 -m venv venv

# Activate the virtual environment
# On Mac/Linux:
source venv/bin/activate
# On Windows:
# .\venv\Scripts\activate

# Install required packages
pip install pytest
pip install garminconnect  # Based on your imports, you'll need this too

# Verify installation
pytest --version
