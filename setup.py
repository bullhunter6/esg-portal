from setuptools import setup, find_packages

setup(
    name="esg_portal",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask",
        "flask-sqlalchemy",
        "flask-migrate",
        "flask-login",
        "flask-wtf",
        "psycopg2-binary",
        "pandas",
        "python-dateutil",
        "email-validator",
        "python-dotenv",
    ],
) 