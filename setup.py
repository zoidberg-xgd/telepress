from setuptools import setup, find_packages

setup(
    name="telepress",
    version="0.3.1",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "telegraph",
        "markdown",
        "requests",
        "Pillow"
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
    author="zoidberg-xgd",
    author_email="",
    description="Publish Markdown to Telegraph with external image hosting support",
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
        "Programming Language :: Python :: 3.12",
    ],
    url="https://github.com/zoidberg-xgd/telepress",
    project_urls={
        "Bug Reports": "https://github.com/zoidberg-xgd/telepress/issues",
        "Source": "https://github.com/zoidberg-xgd/telepress",
    },
    keywords=["telegraph", "markdown", "publishing", "image-hosting", "imgbb", "imgur", "r2"],
)
