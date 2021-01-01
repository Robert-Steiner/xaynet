from setuptools import setup
from setuptools_rust import Binding, RustExtension

install_requires = ["justbackoff==0.6.0"]

dev_require = [
    "black",
    "mypy",
    "pylint",
    "isort",
]

setup(
    name="xaynet-sdk",
    version="0.1.0",
    description="The Xayn Network project is building a privacy layer for machine learning so that AI projects can meet compliance such as GDPR and CCPA. The approach relies on Federated Learning as enabling technology that allows production AI applications to be fully privacy compliant.",
    url="https://github.com/xaynetwork/xaynet/",
    author=["Xayn Engineering"],
    author_email="engineering@xaynet.dev",
    license="Apache License Version 2.0",
    python_requires=">=3.6",
    packages=["xaynet_sdk"],
    rust_extensions=[RustExtension("xaynet_sdk.xaynet_sdk", binding=Binding.PyO3)],
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
        "dev": dev_require,
    },
)
