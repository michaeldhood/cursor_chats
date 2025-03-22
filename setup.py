"""
Setup script for the cursor_chats package.
"""
from setuptools import setup, find_packages

setup(
    name="cursor_chats",
    version="0.1.0",
    description="Tools for extracting and processing Cursor AI chat logs",
    author="Cursor User",
    author_email="user@example.com",
    url="https://github.com/username/cursor-chats",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.0.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "cursor-chats=src.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
) 