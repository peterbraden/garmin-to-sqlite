# Create a virtual environment
python3.12 -m venv venv

# Activate the virtual environment
# On Mac/Linux:
source venv/bin/activate
# On Windows:
# .\venv\Scripts\activate

# Install required packages
pip install pytest
pip install garminconnect
pip install black

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
pytest --version
black --version