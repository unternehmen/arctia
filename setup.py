from setuptools import setup, find_packages

setup(
    name='arctia',
    version='0.1.0',
    packages=find_packages(),
    install_requires=['pygame==1.9.3', 'pytmx==3.21.5'],
    entry_points={
        'console_scripts': [
            'arctia = arctia:main'
        ]
    },
    test_suite = 'nose.collector'
)
