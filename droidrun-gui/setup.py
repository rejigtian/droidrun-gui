from setuptools import setup, find_packages

setup(
    name="droidrun-gui",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.4.0",
        "droidrun>=0.1.0",
        "python-dotenv>=0.19.0",
    ],
    entry_points={
        "console_scripts": [
            "droidrun-gui=droidrun_gui.src.__main__:main",
        ],
    },
    author="Rejig Tian",
    author_email="875283604@qq.com",
    description="A GUI wrapper for DroidRun",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/rejigtian/droidrun-gui.git",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 