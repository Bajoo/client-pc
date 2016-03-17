# -*- coding: utf-8 -*-


def pytest_addoption(parser):
    parser.addoption("--slowtest", action="store_const", default=False,
                     const=True, help="Enable slow tests")
