from setuptools import setup

setup(name="moleskin",
      description="A print and debugging utility that makes your error printouts look nice",
      long_description="Moleskin makes it easy to make pretty debug and color prints in terminals, time function "
                       "calls, and diff current repo with git diff.",
      version="0.1.0",
      url="https://github.com/episodeyang/moleskin",
      author="Ge Yang",
      author_email="yangge1987@gmail.com",
      license=None,
      keywords=["moleskin", "logging", "debug", "debugging", "timer", "timeit", "decorator",
                "stopwatch", "tic", "toc"],
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Science/Research",
          "Programming Language :: Python :: 3"
      ],
      packages=["moleskin"],
      install_requires=["termcolor", "pprint"]
      )
