import os
from setuptools import setup

PACKAGE = "cloudbeat-pytest"

classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Framework :: Pytest',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Topic :: Software Development :: Quality Assurance',
    'Topic :: Software Development :: Testing',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3 :: Only',
]

setup_requires = [
    "setuptools_scm"
]

install_requires = [
    "cloudbeat_common"
]


def prepare_version():
    from setuptools_scm import get_version
    configuration = {"root": "..", "relative_to": __file__}
    version = get_version(**configuration)
    install_requires.append(f"cloudbeat_common=={version}")
    return configuration


def get_readme(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def main():
    setup(
        name=PACKAGE,
        use_scm_version=prepare_version,
        setup_requires=setup_requires,
        install_requires=install_requires,
        description="CloudBeat Pytest Kit",
        url="https://cloudbeat.io",
        project_urls={
            "Source": "https://github.com/cloudbeat-io/cb-kit-python",
        },
        author="CBNR Cloud Solutions LTD",
        author_email="info@cloudbeat.io",
        license="Apache-2.0",
        classifiers=classifiers,
        keywords="cloudbeat testing reporting python pytest",
        #        long_description=get_readme("README.md"),
        long_description_content_type="text/markdown",
        packages=["cloudbeat_pytest"],
        package_dir={"cloudbeat_pytest": 'src'},
        entry_points={"pytest11": ["cloudbeat_pytest = cloudbeat_pytest.plugin"]},
        py_modules=['cloudbeat_pytest'],
        python_requires='>=3.8'
    )


if __name__ == '__main__':
    main()
