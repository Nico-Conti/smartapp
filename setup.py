from setuptools import setup, find_packages

setup(
    name="ai_smartapp",
    version="0.1",
    packages=find_packages(where="../smartapp"),
    package_dir={"": "../smartapp"},
)