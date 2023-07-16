#!/usr/bin/python
######################################################################################################################
#
# Copyright (c) 2022 Marvell International Ltd. 
# All Rights Reserved.
#
# This file contains information that is confidential and proprietary to Marvell International Ltd. Commercial use of 
# this code is subject to licensing terms and is permitted only on semiconductor devices manufactured by or on behalf 
# of Marvell International Ltd or its affiliates. Distribution subject to written consent from Marvell International Ltd.
#
######################################################################################################################

import pytest
import sys
import subprocess
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')

def pytest_addoption(parser):
    parser.addoption(
        "--pi_info",
        dest="pi_info",
        action="store",
        default="0.0.0.0;/home/pi/FTE/USECASE/Vega_CI_Script/RPI;e1.s",
        help="Pi_IP;Path;Board"
    )
#    pi_info = "10.18.151.229;/home/pi/temp_test/FTE/USECASE/Vega_CI_Script/RPI;e1.s"

@pytest.fixture(scope="class")
def pi_info(request):
    return request.config.getoption("--pi_info")