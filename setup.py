
from setuptools import setup, find_packages

setup(
    name="subtitle_generator",
    version="0.1.0",
    description="Video subtitle generator tool with LLM and translation optimization",
    author="Sauterne",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "openai",
        "moviepy",
        "whisper",
        "torch",
        "librosa",
        "soundfile",
        "tqdm",
        "googletrans==4.0.0rc1"
    ],
    entry_points={
        "console_scripts": [
            "subtitle_generator=subtitle_generator.cli:main"
        ],
    },
)
