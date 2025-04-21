from os import path

from setuptools import setup, find_packages

with open(path.join(path.abspath(path.dirname(__file__)), 'README'), encoding='utf-8') as f:
    long_description = f.read()
with open(path.join(path.abspath(path.dirname(__file__)), 'VERSION'), encoding='utf-8') as f:
    version = f.read()
with open(path.join(path.abspath(path.dirname(__file__)), 'LICENSE'), encoding='utf-8') as f:
    license = f.read()

setup(
    name="jaynes",
    description="A tool for running python code with runner on aws",
    long_description=long_description,
    version=version,
    url="https://github.com/episodeyang/jaynes",
    author="Ge Yang",
    author_email="yangge1987@gmail.com",
    license=license,
    keywords=["jaynes", "logging", "DEBUG", "debugging", "timer",
              "timeit", "decorator", "stopwatch", "tic", "toc",
              ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3"
    ],
    packages=find_packages(),
    install_requires=[
        "aiofile",
        "cloudpickle==3.1.1",
        "functional_notations",
        "params-proto>=2.10.0",
        "pyyaml",
        "requests",
        "termcolor",
    ]
)
