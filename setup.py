from setuptools import setup

with open('README.md') as fp:
    long_description = fp.read()

setup(
    name='rss2sql',
    version='1.0.4',
    description='Convert RSS feed to SQL database',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Hu Zheyang',
    author_email='i@huzheyang.com',
    url='https://github.com/jsjyhzy/rss2sql',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
    ],
    python_requires='>=3',
    install_requires=[
        "PyYAML>=3.13",
        "requests>=2.19.1",
        "SQLAlchemy>=1.2.10",
        "feedparser>=5.2.1",
    ],
    packages=['rss2sql'],
    entry_points={
        'console_scripts': [
            'rss2sql=rss2sql.rss2sql:entrypoint',
        ],
    },
)
