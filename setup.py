from setuptools import setup, find_packages


setup(
    name='lus4n',
    packages=find_packages(),
    version='1.2.0',
    install_requires=[
        "networkx~=3.4.2",
        "joblib==1.4.2",
        "xxhash~=3.5.0",
        "tqdm~=4.67.1",
        "loguru~=0.7.3",
        "luaparser~=3.3.0",
        "pyvis~=0.3.2",
        "PySide6~=6.8.2.1"
    ],
    entry_points={
        'console_scripts': [
            'lus4n=lus4n.cli:main'
        ]
    }
)