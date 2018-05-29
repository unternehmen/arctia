from setuptools import setup, find_packages

requirements = ['pygame==1.9.3', 'pytmx==3.21.5']

setup(
    name='arctia',
    version='0.1.0',
    packages=find_packages(),
    install_requires=requirements,
    include_package_data=True,
    tests_require=['nose==1.3.7'] + requirements,
    entry_points={
        'console_scripts': [
            'arctia = arctia:main'
        ]
    },
    test_suite = 'nose.collector'
)
