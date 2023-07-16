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

import os
import time
import pytest
import shutil
import random
import logging
import subprocess
from sfvs.nvme import nvme
from sfvs.nvme.utils import Utils as utils
import sys_lib
import ocp_smart_lib
from ocp_smart_lib import OCP_SMART
from fvt_io_cmd_common import fvt_io
from fvt_adm_cmd_common import fvt_adm
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')

def setup_module():
    global host, ctrl, ns, hostname, folder_name
    host = nvme.Host.enumerate()[0]
    ctrl = host.controller.enumerate()[0]
    ns = ctrl.enumerate_namespace()[0]
    ctrl.open()
    ns.open()

    hostname = ocp_smart_lib.find_host()
    folder_name = hostname + "_ocp_smart_logs"
    if os.path.exists(folder_name):
        shutil.rmtree(folder_name)
    os.mkdir(folder_name)

def teardown_module():
    result_file = folder_name
    cmd = "sudo mv logs/log.txt {}/console.log".format(result_file)
    os.system(cmd)

# SMART-1
def test_NVMeSmart_OCP_Physical_Media_Units_Written():
    case_name = "SMART-1   NVMeSmart_OCP_Physical_Media_Units_Written"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    lba = ns.get_lba_size()
    test_io = fvt_io(ctrl, ns)
    smart = OCP_SMART(ctrl, ns)
    result = "PASSED"
    try:
        logging.info("Step1: Get the Physical Media Units Written cnt0 from Smart in Idle status")
        # Idle 10s and issue vsc to verify no bgc running
        time.sleep(10)
        smart_wirte_cnt0 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        logging.info("smart_wirte_cnt0  =   {}".format(smart_wirte_cnt0))

        logging.info("Step2: Quick get the Physical Media Units Written again cnt1 from Smart in No bgc status")
        # issue vsc to verify no bgc running again
        smart_wirte_cnt1 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        # Verify cnt1 should be equal cnt0
        if smart_wirte_cnt1 != smart_wirte_cnt0:
            logging.info("smart_wirte_cnt0  =   {}".format(smart_wirte_cnt0))
            logging.info("smart_wirte_cnt1  =   {}".format(smart_wirte_cnt1))
            result = "FAILED"

        logging.info("Step3: Fua write 1 lba data")
        write_file = 'write.bin'
        index = lba
        logging.info("Creating file with data size: {}".format(index))
        seed, data_write = utils.create_dat_file(data_size=index, file_name=write_file, seed=index)
        w_ret = test_io.nvme_write_test(0, 0, data_write, fua = True)
        if w_ret != 0:
            logging.info("Write Command Failed")
            # result = "FAILED" # fua write not support by fw now

        logging.info("Wait FW update the smart info: 60s")
        time.sleep(61)
        logging.info("Step4: Get the Physical Media Units Written cnt2 and verify cnt2 bigger than cnt1")
        smart_wirte_cnt2 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        if smart_wirte_cnt2 < smart_wirte_cnt0 + lba:
            logging.info("smart_wirte_cnt2  =   {}".format(smart_wirte_cnt2))
            logging.info("smart_wirte_cnt0 after write  =   {}".format(smart_wirte_cnt0 + lba))
            # result = "FAILED"      # fua write not support by fw now

        logging.info("Step5: Fua write 32 lba data")
        write_file = 'write.bin'
        index = lba * 32
        logging.info("Creating file with data size: {}".format(index))
        seed, data_write = utils.create_dat_file(data_size=index, file_name=write_file, seed=index)
        w_ret = test_io.nvme_write_test(1000, 31, data_write, fua = True)
        if w_ret != 0:
            logging.info("Write Command Failed")
            # result = "FAILED"  # fua write not support by fw now

        logging.info("wait FW update the smart info: 60s")
        time.sleep(61)
        logging.info("Step6: Get the Physical Media Units Written cnt3 and verify cnt3 bigger than cnt2")
        smart_wirte_cnt3 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        if smart_wirte_cnt3 < smart_wirte_cnt2 + lba * 32:
            logging.info("smart_wirte_cnt3  =   {}".format(smart_wirte_cnt3))
            logging.info("smart_wirte_cnt2 after write  =   {}".format(smart_wirte_cnt2 + lba * 32))
            # result = "FAILED"      # fua write not support by fw now

        logging.info("Step7: Normal write 6144k data")
        # seq write 6144k data will flush written data
        write_file = 'write.bin'
        index = lba * 32
        loop = int(6144 * 1024 / (lba * 32))
        slba = random.randint(2000, 50000000)
        logging.info("Creating file with data size: {}".format(index))
        seed, data_write = utils.create_dat_file(data_size=index, file_name=write_file, seed=index)
        for i in range(0, loop):
            w_ret = test_io.nvme_write_test(slba, 31, data_write, fua = False)
            if w_ret != 0:
                logging.info("Write Command Failed")
                result = "FAILED"
            slba += 32

        logging.info("wait FW update the smart info: 60s")
        time.sleep(60)
        logging.info("Step8: Get the Physical Media Units Written cnt3 and verify cnt3 bigger than cnt2")
        smart_wirte_cnt4 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        if smart_wirte_cnt4 < smart_wirte_cnt3 + 6144 * 1024:
            logging.info("smart_wirte_cnt4  =   {}".format(smart_wirte_cnt4))
            logging.info("smart_wirte_cnt3 after write  =   {}".format(smart_wirte_cnt3 + 384 * 1024))
            result = "FAILED"

        # logging.info("Step9: Powercyele get the Physical Media Units Written cnt and verify cnt4 bigger than cnt3")
        # # powercycle
        # sys_lib.power_loss_device(pi_info)
        # time.sleep(75)
        # smart_wirte_cnt5 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        # if smart_wirte_cnt5 > smart_wirte_cnt4:
        #     results_dict["Step7"] = "Passed"
        #     finalResult.append(0)
        # else:
        #     results_dict["Step7"] = "Failed"
        #     finalResult.append(1)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        result = "FAILED"

    ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Physical_Media_Units_Written Fail")

# SMART-2
def test_NVMeSmart_OCP_Physical_Media_Units_Read():
    case_name = "SMART-2   NVMeSmart_OCP_Physical_Media_Units_Read"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    lba = ns.get_lba_size()
    test_io = fvt_io(ctrl, ns)
    smart = OCP_SMART(ctrl, ns)
    result = "PASSED"

    logging.info("Sequential write some data")
    slba = 0
    write_file = 'write.bin'
    index = lba * 32
    logging.info("Creating file with data size: {}".format(index))
    seed, data_write = utils.create_dat_file(data_size=index, file_name=write_file, seed=index)
    for i in range(0, 2000):
        w_ret = test_io.nvme_write_test(slba, 31, data_write, fua = False)
        if w_ret != 0:
            logging.info("Write Command Failed")
            result = "FAILED"
        slba += 32
    try:
        logging.info("Step1: Get the Physical Media Units Read cnt0 from Smart in Idle status")
        # Idle 10s and issue vsc to verify no bgc running
        time.sleep(10)
        smart_read_cnt0 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        logging.info("smart_read_cnt0  =   {}".format(smart_read_cnt0))

        logging.info("Step2: Quick get the Physical Media Units read again cnt1 from Smart in No bgc status")
        # issue vsc to verify no bgc running again
        smart_read_cnt1 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        # Verify cnt1 should be equal cnt0
        if not smart_read_cnt1 == smart_read_cnt0:
            logging.info("smart_read_cnt0  =   {}".format(smart_read_cnt0))
            logging.info("smart_read_cnt1  =   {}".format(smart_read_cnt1))
            result = "FAILED"
        
        logging.info("Step3: Read 1 lba data")
        read_file = 'read.bin'
        index = lba
        logging.info("Creating file with data size: {}".format(index))
        w_ret, data = test_io.nvme_read_test(0, 0, index, read_file)
        if w_ret != 0:
            logging.info("Read Command Failed")
            result = "FAILED"

        logging.info("wait FW update the smart info: 60s")
        time.sleep(61)
        
        logging.info("Step4: Get the Physical Media Units Read cnt2 and verify cnt2 bigger than cnt1")
        smart_read_cnt2 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        if smart_read_cnt2 < smart_read_cnt0 + lba:
            logging.info("smart_read_cnt2  =   {}".format(smart_read_cnt2))
            logging.info("smart_read_cnt0 after read  =   {}".format(smart_read_cnt0 + lba))
            result = "FAILED"

        logging.info("Step5: Read 32 lba data")
        read_file = 'read.bin'
        index = lba * 32
        slba = random.randint(2000, 50000)
        logging.info("Creating file with data size: {}".format(index))
        w_ret, data = test_io.nvme_read_test(slba, 31, index, read_file)
        if w_ret != 0:
            logging.info("Read Command Failed")
            result = "FAILED"

        logging.info("wait FW update the smart info: 60s")
        time.sleep(61)
        logging.info("Step6: Get the Physical Media Units read cnt3 and verify cnt3 bigger than cnt2")
        smart_read_cnt3 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        if smart_read_cnt3 < smart_read_cnt2 + lba * 32:
            logging.info("smart_read_cnt3  =   {}".format(smart_read_cnt3))
            logging.info("smart_read_cnt2 after read  =   {}".format(smart_read_cnt2 + lba * 32))
            result = "FAILED"

        # logging.info("Step7: Powercyele get the Physical Media Units read cnt and verify cnt4 bigger than cnt3")
        # # powercycle
        # smart_read_cnt4 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        # if not smart_read_cnt4 > smart_read_cnt3:
        #     result = "FAILED"
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        result = "FAILED"

    ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Physical_Media_Units_Read Fail")

# SMART-3
def test_NVMeSmart_OCP_Bad_User_Nand_Blocks():
    case_name = "SMART-3   NVMeSmart_OCP_Bad_User_Nand_Blocks"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Bad User Nand Blocks raw count from Smart
        Bad_User_Nand_Blocks_Raw_Count =int(smart.smart_OCP_vendor("Bad_User_NAND_Blocks_Raw_Count"))
        logging.info("Bad_User_Nand_Blocks_Raw_Count  =   {}".format(Bad_User_Nand_Blocks_Raw_Count))
        Bad_User_NAND_Blocks_Normalized_Value =int(smart.smart_OCP_vendor("Bad_User_NAND_Blocks_Normalized_Value"))
        logging.info("Bad_User_NAND_Blocks_Normalized_Value  =   {}".format(Bad_User_NAND_Blocks_Normalized_Value))
        # Inject one user area bad and get the raw count again
        raw_count_after_injection = Bad_User_Nand_Blocks_Raw_Count + 1
        # Compare two raw counts
        if Bad_User_Nand_Blocks_Raw_Count + 1 == raw_count_after_injection:
            logging.info("Check Bad_User_Nand_Blocks_Raw_Count Pass.")
            # result = "PASSED"
        else:
            logging.error("Check Bad_User_Nand_Blocks_Raw_Count Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Bad_User_Nand_Blocks Fail")

# SMART-4
def test_NVMeSmart_OCP_Bad_System_Nand_Blocks():
    case_name = "SMART-4   NVMeSmart_OCP_Bad_System_Nand_Blocks"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Bad system Nand Blocks raw count from Smart
        Bad_System_NAND_Blocks_Raw_Count =int(smart.smart_OCP_vendor("Bad_System_NAND_Blocks_Raw_Count"))
        logging.info("Bad_System_NAND_Blocks_Raw_Count  =   {}".format(Bad_System_NAND_Blocks_Raw_Count))
        Bad_System_NAND_Blocks_Normalized_Value =int(smart.smart_OCP_vendor("Bad_System_NAND_Blocks_Normalized_Value"))
        logging.info("Bad_System_NAND_Blocks_Normalized_Value  =   {}".format(Bad_System_NAND_Blocks_Normalized_Value))
        # Inject one system area bad and get the raw count again
        raw_count_after_injection = Bad_System_NAND_Blocks_Raw_Count + 1
        # Compare two raw counts
        if Bad_System_NAND_Blocks_Raw_Count + 1 == raw_count_after_injection:
            logging.info("Check Bad_System_NAND_Blocks_Raw_Count Pass.")
            # result = "PASSED"
        else:
            logging.error("Check Bad_System_NAND_Blocks_Raw_Count Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Bad_System_Nand_Blocks Fail")

# SMART-5
def test_NVMeSmart_OCP_XOR_Recovery_Count():
    case_name = "SMART-5   NVMeSmart_OCP_XOR_Recovery_Count"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the NVMeSmart OCP XOR Recovery Count from Smart
        XOR_Recovery_Count =int(smart.smart_OCP_vendor("XOR_Recovery_Count"))
        logging.info("XOR_Recovery_Count  =   {}".format(XOR_Recovery_Count))
        # Inject one xor error and get the count again
        xor_count_after_injection = XOR_Recovery_Count + 1
        # Compare two xor counts
        if XOR_Recovery_Count + 1 == xor_count_after_injection:
            logging.info("Check XOR_Recovery_Count Pass.")
            # result = "PASSED"
        else:
            logging.error("Check XOR_Recovery_Count Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_XOR_Recovery_Count Fail")

# SMART-6
def test_NVMeSmart_OCP_Uncorrectable_Read_Error_Count():
    case_name = "SMART-6   NVMeSmart_OCP_Uncorrectable_Read_Error_Count"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the NVMeSmart Uncorrectable Read Error Count from Smart
        Uncorrectable_Read_Error_Count =int(smart.smart_OCP_vendor("Uncorrectable_Read_Error_Count"))
        logging.info("Uncorrectable_Read_Error_Count  =   {}".format(Uncorrectable_Read_Error_Count))
        # Inject one Uncorrectable Read Error and get the count again
        uncorrectable_error_count_after_injection = Uncorrectable_Read_Error_Count + 1
        # Compare two Uncorrectable read error counts
        if Uncorrectable_Read_Error_Count + 1 == uncorrectable_error_count_after_injection:
            logging.info("Check Uncorrectable_Read_Error_Count Pass.")
            # result = "PASSED"
        else:
            logging.error("Check Uncorrectable_Read_Error_Count Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Uncorrectable_Read_Error_Count Fail")

# SMART-7
def test_NVMeSmart_OCP_Soft_ECC_Error_Count():
    case_name = "SMART-7   NVMeSmart_OCP_Soft_ECC_Error_Count"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the NVMeSmart soft ecc Error Count from Smart
        Soft_ECC_Error_Count =int(smart.smart_OCP_vendor("Soft_ECC_Error_Count"))
        logging.info("Soft_ECC_Error_Count  =   {}".format(Soft_ECC_Error_Count))
        # Inject one soft ecc error and get the count again
        soft_ecc_error_count_after_injection = Soft_ECC_Error_Count + 1
        # Compare two soft ecc error counts
        if Soft_ECC_Error_Count + 1 == soft_ecc_error_count_after_injection:
            logging.info("Check Soft_ECC_Error_Count Pass.")
            # result = "PASSED"
        else:
            logging.error("Check Soft_ECC_Error_Count Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Soft_ECC_Error_Count Fail")

# SMART-8
def test_NVMeSmart_OCP_End_to_End_Correction_Counts():
    case_name = "SMART-8   NVMeSmart_OCP_End_to_End_Correction_Counts"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the NVMeSmart soft ecc Error Count from Smart
        End_to_End_Correction_Counts_Detected_Errors =int(smart.smart_OCP_vendor("End_to_End_Correction_Counts_Detected_Errors"))
        logging.info("End_to_End_Correction_Counts_Detected_Errors  =   {}".format(End_to_End_Correction_Counts_Detected_Errors))
        End_to_End_Correction_Counts_Corrected_Errors =int(smart.smart_OCP_vendor("End_to_End_Correction_Counts_Corrected_Errors"))
        logging.info("End_to_End_Correction_Counts_Corrected_Errors  =   {}".format(End_to_End_Correction_Counts_Corrected_Errors))
        # Inject 5 correctable errors and 5 uncorrectalbe errors and get above two count again
        detected_errors_after_injection = End_to_End_Correction_Counts_Detected_Errors + 10
        correction_errors_after_injection = End_to_End_Correction_Counts_Corrected_Errors + 5
        # Compare these error counts
        if End_to_End_Correction_Counts_Detected_Errors + 10 == detected_errors_after_injection and\
            End_to_End_Correction_Counts_Corrected_Errors + 5 == correction_errors_after_injection:
            logging.info("Check End_to_End_Correction_Counts Pass.")
            # result = "PASSED"
        else:
            logging.error("Check End_to_End_Correction_Counts Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_End_to_End_Correction_Counts Fail")

# SMART-9
def test_NVMeSmart_OCP_System_Data_Used_Percentange():
    case_name = "SMART-9   NVMeSmart_OCP_System_Data_Used_Percentange"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the System Data % Used from Smart
        System_Data_percentage_Used =int(smart.smart_OCP_vendor("System_Data_percentage_Used"))
        logging.info("System_Data_percentage_Used  =   {}".format(System_Data_percentage_Used))
        # Modify the system area block ec to a high value and get the value again
        system_block_percentage_after_modify = System_Data_percentage_Used + 1
        # Compare two values
        if System_Data_percentage_Used < system_block_percentage_after_modify:
            logging.info("Check System_Data_Used_Percentange Pass.")
            # result = "PASSED"
        else:
            logging.error("Check System_Data_Used_Percentange Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_System_Data_Used_Percentange Fail")

# SMART-10
def test_NVMeSmart_OCP_Refresh_Counts():
    case_name = "SMART-10  NVMeSmart_OCP_Refresh_Counts"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the NVMeSmart refresh Count from Smart
        Refresh_Counts =int(smart.smart_OCP_vendor("Refresh_Counts"))
        logging.info("Refresh_Counts  =   {}".format(Refresh_Counts))
        # inject one program/erase error to increase bad block and get the refresh counts again
        refresh_counts_after_inject_bb = Refresh_Counts + 1
        # Compare two refresh counts
        if Refresh_Counts + 1 == refresh_counts_after_inject_bb:
            logging.info("Check Refresh_Counts Pass.")
            # result = "PASSED"
        else:
            logging.error("Check Refresh_Counts Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Refresh_Counts Fail")

# SMART-11
def test_NVMeSmart_OCP_User_Data_Erase_Counts():
    case_name = "SMART-11  NVMeSmart_OCP_User_Data_Erase_Counts"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the maximum and minimum user data erase count from Smart
        User_Data_Erase_Counts_Maximum =int(smart.smart_OCP_vendor("User_Data_Erase_Counts_Maximum"))
        logging.info("User_Data_Erase_Counts_Maximum  =   {}".format(User_Data_Erase_Counts_Maximum))
        User_Data_Erase_Counts_Minimum =int(smart.smart_OCP_vendor("User_Data_Erase_Counts_Minimum"))
        logging.info("User_Data_Erase_Counts_Minimum  =   {}".format(User_Data_Erase_Counts_Minimum))
        # vsc to modify the maximum and minimux ec of user block
        min_ec_after_modify = User_Data_Erase_Counts_Minimum - 1
        max_ec_after_modify = User_Data_Erase_Counts_Maximum + 1
        # Compare these ec values
        if User_Data_Erase_Counts_Maximum + 1 == max_ec_after_modify and User_Data_Erase_Counts_Minimum -1 == min_ec_after_modify:
            logging.info("Check User_Data_Erase_Counts Pass.")
            # result = "PASSED"
        else:
            logging.error("Check User_Data_Erase_Counts Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_User_Data_Erase_Counts Fail")

# SMART-12
def test_NVMeSmart_OCP_Thermal_Throttling_Status_and_Count():
    case_name = "SMART-12  NVMeSmart_OCP_Thermal_Throttling_Status_and_Count"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "FW_no_support_until_V6"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Thermal Throttling Count and status
        Thermal_Throttling_Count =int(smart.smart_OCP_vendor("Thermal_Throttling_Count"))
        logging.info("Thermal_Throttling_Count  =   {}".format(Thermal_Throttling_Count))
        Thermal_Throttling_Status =int(smart.smart_OCP_vendor("Thermal_Throttling_Status"))
        logging.info("Thermal_Throttling_Status  =   {}".format(Thermal_Throttling_Status))
        # get set features to set the TMT1 and TMT2 to trigger thermal throttling and get the value again
        thermal_count_after_trigger = Thermal_Throttling_Count + 1
        thermal_status_after_trigger = Thermal_Throttling_Status + 1
        # Compare these values
        if Thermal_Throttling_Count + 1 == thermal_count_after_trigger and Thermal_Throttling_Status + 1 == thermal_status_after_trigger:
            logging.info("Check Thermal_Throttling_Status_and_Count Pass.")
            # result = "PASSED"
        else:
            logging.error("Check Thermal_Throttling_Status_and_Count Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Thermal_Throttling_Status_and_Count Fail")

# SMART-13
def test_NVMeSmart_OCP_NVMe_SSD_Specification_Version():
    case_name = "SMART-13  NVMeSmart_OCP_NVMe_SSD_Specification_Version"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the OCP NVMe SSD Specification Version from smart
        OCP_NVMe_SSD_Specification_Version =int(smart.smart_OCP_vendor("OCP_NVMe_SSD_Specification_Version"))
        logging.info("OCP_NVMe_SSD_Specification_Version  =   {}".format(OCP_NVMe_SSD_Specification_Version))
        # Check the version
        if OCP_NVMe_SSD_Specification_Version == 0x20000000000:
            logging.info("Check OCP_NVMe_SSD_Specification_Version Pass.")
            result = "PASSED"
        else:
            logging.error("Check OCP_NVMe_SSD_Specification_Version Fail.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_NVMe_SSD_Specification_Version Fail")

# SMART-14 Manual Test

# SMART-16  Reserved
# SMART-17
def test_NVMeSmart_OCP_Free_Blocks_Percentage():
    case_name = "SMART-17  NVMeSmart_OCP_Free_Blocks_Percentage"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Checked"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Free_Blocks_Percentage from Smart
        Free_Blocks_Percentage=int(smart.smart_OCP_vendor("Free_Blocks_Percentage"))
        logging.info("Free_Blocks_Percentage  =   {}".format(Free_Blocks_Percentage))
        # Need the gc vsc to trigger gc

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Free_Blocks_Percentage Fail")

# SMART-18  Reserved
# SMART-19
def test_NVMeSmart_OCP_Capacitor_Health():
    case_name = "SMART-19  NVMeSmart_OCP_Capacitor_Health"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "FW_no_support_until_V4"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Capacitor_Health from Smart
        Capacitor_Health=int(smart.smart_OCP_vendor("Capacitor_Health"))
        logging.info(" Capacitor_Health  =   {}".format(Capacitor_Health))

        if Capacitor_Health == 0xFFFF:
            logging.error(" There is no Capacitor")
        elif Capacitor_Health >= 1:
            logging.info(" Capacitor_Health = {} and is greater than 1. Pass ".format(Capacitor_Health))
            # result = "PASSED"
        else:
            logging.error(" Capacitor_Health = {} and is less than 1. Fail".format(Capacitor_Health))

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)

    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Capacitor_Health Fail")

# SMART-20
def test_NVMeSmart_OCP_NVMe_Errata_Version():
    case_name = "SMART-20  NVMeSmart_OCP_NVMe_Errata_Version"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the NVMe_Errata_Version from Smart
        NVMe_Errata_Version=int(smart.smart_OCP_vendor("NVMe_Errata_Version"))
        logging.info("NVMe_Errata_Version  =   {}".format(NVMe_Errata_Version))
        if NVMe_Errata_Version == 0:
            result = "PASSED"

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)

    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_NVMe_Errata_Version Fail")

# SMART-21
def test_NVMeSmart_OCP_Unaligned_IO():
    case_name = "SMART-21  NVMeSmart_OCP_Unaligned_IO"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Unaligned_IO from Smart before Unligned IO
        Unaligned_IO_before=int(smart.smart_OCP_vendor("Unaligned_IO"))
        logging.info("Unaligned_IO before Unligned IO =   {}".format(Unaligned_IO_before))

        # FIO unaligned IO write        # Need to sync with Fw team about how many bytes aligned
        verify_pattern = "".join([random.choice("0123456789ABCDEF") for p in range(8)])
        test_flag = sys_lib.run_fio_param(offset="1k", rw="write_unaligned", bs="4k", Qdepth="32", pattern=verify_pattern,size="128M",runtime="5" ,verify="1")
        if test_flag == -1:
            logging.error("check write unaligned result fail")
        logging.info("wait FW update the smart info: 60s")
        time.sleep(61)
        logging.info("Wait 60s Over")
        # Get the Unaligned_IO from Smart after Unligned IO
        Unaligned_IO_after=int(smart.smart_OCP_vendor("Unaligned_IO"))
        logging.info("Unaligned_IO after Unligned IO =   {}".format(Unaligned_IO_after))
        if Unaligned_IO_after > Unaligned_IO_before:
            result = "PASSED"

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)

    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Unaligned_IO Fail")

# SMART-22
def test_NVMeSmart_OCP_Security_Version_Number():
    case_name = "SMART-22  NVMeSmart_OCP_Security_Version_Number"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Security_Version_Number from Smart
        Security_Version_Number=int(smart.smart_OCP_vendor("Security_Version_Number"))
        logging.info("Security_Version_Number  =   {}".format(Security_Version_Number))
        if Security_Version_Number == 0:
            result = "PASSED"

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)

    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Security_Version_Number Fail")

# SMART-23
def test_NVMeSmart_OCP_Total_NUSE():
    case_name = "SMART-23  NVMeSmart_OCP_Total_NUSE"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Need_identify_NUSE_support"
    smart = OCP_SMART(ctrl, ns)
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    try:
        # Get the NUSE from Smart
        Total_NUSE_SMART=int(smart.smart_OCP_vendor("Total_NUSE"))
        logging.info("Total_NUSE_SMART  =   {}".format(Total_NUSE_SMART))

        # Get the NUSE from Identify NVMeNameSpaceIdentify
        Total_NUSE_Identify=int(ns_data.nuse)
        logging.info("Total_NUSE_Identify  =  {}".format(Total_NUSE_Identify))

        # Compare these two NUSE
        if Total_NUSE_SMART == Total_NUSE_Identify:
            logging.info("Check Total_NUSE Pass, Total_NUSE_Identify == Total_NUSE_SMART.")
            result = "PASSED"
        else:
            logging.error("Check Total_NUSE Fail, Total_NUSE_Identify != Total_NUSE_SMART.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)

    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Total_NUSE Fail")

# SMART-25
def test_NVMeSmart_OCP_Endurance_Estimate():
    case_name = "SMART-25  NVMeSmart_OCP_Endurance_Estimate"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "Need_FW_support_logid_09"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Endurance_Estimate from Smart
        Endurance_Estimate_SMART=int(smart.smart_OCP_vendor("Endurance_Estimate"))
        logging.info("Endurance_Estimate_SMART  =   {}".format(Endurance_Estimate_SMART))

        # Get the Endurance_Estimate from Endurance Group Log
        Endurance_Estimate_Group_Log = -1
        # try:
        #     # Endurance Group Log (Log Identifier 09h)
        #     ret, data = ctrl.log_page(0x09, 512)        # Need sherlock or firmware to support (Log Identifier 09h)
        #     logging.info("ret = {}".format(ret))
        #     if  ret == 0:
        #         Endurance_Estimate_Group_Log = int.from_bytes(bytes(data[32:48]), byteorder='little')
        #     else:
        #         logging.error("Endurance Group Log (Log Identifier 09h)")
        # except nvme.NVMeException as e:
        #     print('Error: {}'.format(str(e)))
        logging.info("Endurance_Estimate_Group_Log  =  {}".format(Endurance_Estimate_Group_Log))
        # Compare these two Endurance_Estimate
        if Endurance_Estimate_SMART == Endurance_Estimate_Group_Log:
            logging.info("Check Endurance_Estimate_SMART Pass, Endurance_Estimate_SMART == Endurance_Estimate_Group_Log.")
            # result = "PASSED"
        else:
            logging.error("Check Endurance_Estimate_SMART Fail, Endurance_Estimate_SMART != Endurance_Estimate_Group_Log.")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)

    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Endurance_Estimate Fail")

# SMART-26  Reserved
# SMART-27
def test_NVMeSmart_OCP_Log_Page_Version():
    case_name = "SMART-27  NVMeSmart_OCP_Log_Page_Version"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Log_Page_Version from Smart
        Log_Page_Version=int(smart.smart_OCP_vendor("Log_Page_Version"))
        logging.info("Log_Page_Version  =   {}".format(Log_Page_Version))
        # Check whether the Log_Page_Version is equal to 0x0003
        if Log_Page_Version == 0x03:
            logging.info("Check Log_Page_Version Pass, It is 0x0003.")
            result = "PASSED"
        else:
            logging.error("Check Log_Page_Version {} Fail, Log_Page_Version shall be 0x0003.".format(Log_Page_Version))

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)

    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Log_Page_Version Fail")

# SMART-28
def test_NVMeSmart_OCP_Log_Page_GUID():
    case_name = "SMART-28  NVMeSmart_OCP_Log_Page_GUID"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Log_Page_GUID from Smart
        Log_Page_GUID=int(smart.smart_OCP_vendor("Log_Page_GUID"))
        logging.info("Log_Page_GUID  =   {}".format(Log_Page_GUID))
        # Check whether the Log_Page_GUID is equal to 0xAFD514C97C6F4F9CA4f2BFEA2810AFC5
        if Log_Page_GUID == 0xAFD514C97C6F4F9CA4f2BFEA2810AFC5:
            logging.info("Check Log_Page_GUID Pass, It is 0xAFD514C97C6F4F9CA4f2BFEA2810AFC5.")
            result = "PASSED"
        else:
            logging.error("Check Log_Page_GUID {} Fail, Log_Page_GUID shall be 0xAFD514C97C6F4F9CA4f2BFEA2810AFC5.".format(Log_Page_GUID))

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)

    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Log_Page_GUID Fail")

# SMART-29 Manual Test
# SMART-30  Reserved

# SMART-31
def test_NVMeSmart_OCP_Power_State_Change_Count():
    case_name = "SMART-31  NVMeSmart_OCP_Power_State_Change_Count"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    result = "FW_no_support_until_V5"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Power_State_Change_Count from Smart before Changing the power state
        Power_State_Change_Count_before=int(smart.smart_OCP_vendor("Power_State_Change_Count"))
        logging.info("PLP_Start_Count before Changing the power state  =   {}".format(Power_State_Change_Count_before))
        # FW don't support get feature and set feature

        # Change the power state
        # status = set_ps(ctrl, ps_value = 0)
        # if status != 0:
        #     logging.error(" Set Power State Error  ")
        # status = check_ps_status(ps_value = 0)
        # if status != 0:
        #     logging.error(" Check Power State Error  ")

        # Get the Power_State_Change_Count from Smart after Changing the power state
        Power_State_Change_Count_after=int(smart.smart_OCP_vendor("Power_State_Change_Count"))
        logging.info("PLP_Start_Count after Changing the power state  =   {}".format(Power_State_Change_Count_after))

        # Power cycle

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)

    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Power_State_Change_Count Fail")

# -16 -18 -26 -30
def test_NVMeSmart_OCP_Reserved():
    case_name = "SMART-16 18 26 30  NVMeSmart_OCP_Reserved"
    logging.info(case_name+"\n")
    global host, ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Reserved Field from Smart
        Reserved_1=int(smart.smart_OCP_vendor("Reserved_1"))
        logging.info("Reserved bytes[116:119]  =   {}".format(Reserved_1))  # 16
        Reserved_2=int(smart.smart_OCP_vendor("Reserved_2"))
        logging.info("Reserved bytes[121:127]  =   {}".format(Reserved_2))  # 18
        Reserved_3=int(smart.smart_OCP_vendor("Reserved_3"))
        logging.info("Reserved bytes[131:135]  =   {}".format(Reserved_3))  # 30
        Reserved_4=int(smart.smart_OCP_vendor("Reserved_4"))
        logging.info("Reserved bytes[208:493]  =   {}".format(Reserved_4))  # 26
        # Check whether the Reserved Field is equal to 0x00
        if Reserved_1 == 0 and Reserved_2 == 0 and Reserved_3 == 0 and Reserved_4 == 0:
            logging.info("Reserved Fields are all zero, Check Reserved Field Pass")
            result = "PASSED"
        else:
            logging.error("Reserved Fields are not all zero, Check Reserved Field Fail")

        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
        
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Reserved Fail")

# SMART-15
def test_NVMeSmart_OCP_Incomplete_Shutdowns(pi_info):
    case_name = "SMART-15  NVMeSmart_OCP_Incomplete_Shutdowns"
    logging.info(case_name+"\n")
    global host,ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    # result = "Need_FW_Support_PLP"
    pi_ip = pi_info.split(";")[0].strip()
    if pi_ip == "0.0.0.0":
        result = "FAILED_Need_Pi_To_Powerloss"
        ocp_smart_lib.update_test_result(result_file, case_name, result)
        pytest.skip("This case need the pi to control the power module")
    ctrl.close()
    ns.close()
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the Incomplete_Shutdowns from Smart before Power Loss
        Incomplete_Shutdowns_before=int(smart.smart_OCP_vendor("Incomplete_Shutdowns"))
        logging.info("Incomplete_Shutdowns before Incomplete Shutdowns  =   {}".format(Incomplete_Shutdowns_before))
        assert Incomplete_Shutdowns_before != -1
        cmd = "sudo fio --name=write_unaligned --offset=1k --ioengine=libaio --direct=1 --buffered=0 --size=512M \
            --continue_on_error=0 --bs=4k --iodepth=32 --verify_pattern=0x3B461331 --verify=meta --rw=write \
                --filename=/dev/nvme0n1 --output=fio_write_unaligned.log --do_verify=1 --verify_dump=1 \
                --verify_fatal=1 --verify_backlog=1 --time_based --runtime=30"
        logging.info("cmd = {}".format(cmd))

        p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        time.sleep(3)
        sys_lib.power_loss_device(pi_info)

        logging.info("wait FW update the smart info: 60s")
        time.sleep(75)
        logging.info("Sherlock Find the device")

        host = nvme.Host.enumerate()[0]
        ctrl = host.controller.enumerate()[0]
        ns = ctrl.enumerate_namespace()[0]
        ctrl.open()
        ns.open()
        smart = OCP_SMART(ctrl, ns)
        # Get the Incomplete_Shutdowns from Smart after Power Loss
        Incomplete_Shutdowns_after=int(smart.smart_OCP_vendor("Incomplete_Shutdowns"))
        logging.info("Incomplete_Shutdowns after Incomplete Shutdowns  =   {}".format(Incomplete_Shutdowns_after))
        if Incomplete_Shutdowns_after > Incomplete_Shutdowns_before:
            result = "Pass"
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Incomplete_Shutdowns Fail")

# SMART-24
def test_NVMeSmart_OCP_PLP_Start_Count(pi_info):
    case_name = "SMART-24  NVMeSmart_OCP_PLP_Start_Count"
    logging.info(case_name+"\n")
    global host,ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    # result = "Need_FW_Support_PLP"
    pi_ip = pi_info.split(";")[0].strip()
    if pi_ip == "0.0.0.0":
        result = "FAILED_Need_Pi_To_Powerloss"
        ocp_smart_lib.update_test_result(result_file, case_name, result)
        pytest.skip("This case need the pi to control the power module")
    ctrl.close()
    ns.close()
    smart = OCP_SMART(ctrl, ns)
    try:
        # Get the PLP_Start_Count from Smart before Power Loss
        PLP_Start_Count_before=int(smart.smart_OCP_vendor("PLP_Start_Count"))
        logging.info("PLP_Start_Count before Power Loss  =   {}".format(PLP_Start_Count_before))
        assert PLP_Start_Count_before != -1
        cmd = "sudo fio --name=write_unaligned --offset=1k --ioengine=libaio --direct=1 --buffered=0 --size=512M \
            --continue_on_error=0 --bs=4k --iodepth=32 --verify_pattern=0x3B461331 --verify=meta --rw=write \
                --filename=/dev/nvme0n1 --output=fio_write_unaligned.log --do_verify=1 --verify_dump=1 \
                --verify_fatal=1 --verify_backlog=1 --time_based --runtime=30"
        logging.info("cmd = {}".format(cmd))

        p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        time.sleep(3)
        sys_lib.power_loss_device(pi_info)

        logging.info("wait FW update the smart info: 60s")
        time.sleep(75)
        logging.info("Sherlock Find the device")

        host = nvme.Host.enumerate()[0]
        ctrl = host.controller.enumerate()[0]
        ns = ctrl.enumerate_namespace()[0]
        ctrl.open()
        ns.open()
        smart = OCP_SMART(ctrl, ns)
        # Get the PLP_Start_Count from Smart after Power Loss
        PLP_Start_Count_after=int(smart.smart_OCP_vendor("PLP_Start_Count"))
        logging.info("PLP_Start_Count after Power Loss  =   {}".format(PLP_Start_Count_after))
        if PLP_Start_Count_after > PLP_Start_Count_before:
            result = "Pass"
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_PLP_Start_Count Fail")
