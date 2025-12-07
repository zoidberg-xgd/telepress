from setuptools import setup, find_packages

setup(
    name="telepress",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "telegraph",
        "markdown",
        "requests"
    ],
    extras_require={
        "api": [
            "fastapi",
            "uvicorn",
            "python-multipart"
        ],
        "dev": [
            "pytest",
            "pytest-cov",
            "httpx"  # For FastAPI TestClient
        ]
    },
    entry_points={
        'console_scripts': [
            'telepress=telepress.cli:main',
            'telepress-server=telepress.server:main',
        ],
    },
    author="User",
    description="TelePress: A robust framework to publish text, images, and archives to Telegraph.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    url="https://github.com/user/telepress",
)
