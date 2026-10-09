"""
ModelMedic — setup.py
"""
import os
import codecs
from setuptools import setup, find_packages


def read_text(filepath):
    with codecs.open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def read_version():
    for line in read_text("modelmedic/version.py").splitlines():
        if line.startswith("__version__"):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")


here = os.path.dirname(__file__)

setup(
    name="modelmedic",
    version=read_version(),
    description="Intelligent ML diagnosis, explainability, and AI-assistance layer built on ClearML",
    long_description=read_text(os.path.join(here, "README.md")) if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="ModelMedic",
    license="Apache License 2.0",
    python_requires=">=3.9",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    install_requires=read_text(os.path.join(here, "requirements.txt")).splitlines(),
    entry_points={
        "console_scripts": [
            "modelmedic = modelmedic.cli.__main__:main",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "License :: OSI Approved :: Apache Software License",
    ],
)
