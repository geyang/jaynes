from setuptools import setup

setup(name='moleskin',
      description='A print and debugging utility that makes your error printouts look nice',
      long_description='Moleskin makes it easy to print in terminals',
      version='0.0.8',
      url='https://github.com/episodeyang/moleskin',
      author='Ge Yang',
      author_email='yangge1987@gmail.com',
      license=None,
      keywords=['moleskin', 'logging', 'debug', 'debugging', 'timer', 'timeit', 'decorator',
                'stopwatch', 'tic', 'toc'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Science/Research',
          'Programming Language :: Python :: 3'
      ],
      packages=['moleskin'],
      install_requires=['termcolor', 'pprint']
      )
