from setuptools import setup, find_packages

setup(
    name="garmin_sync",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
) 