from setuptools import setup, find_packages

with open("puppets/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"')
            break

setup(
    name="puppets",
    version=version,
    description="Parallel Tor browser automation with Python",
    author="Puppets Contributors",
    author_email="",
    url="https://github.com/PrimalDjinn/puppets",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "undetected-chromedriver>=3.5.0",
        "stem>=1.8.0",
        "requests>=2.28.0",
        "selenium>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "puppets=puppets.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)