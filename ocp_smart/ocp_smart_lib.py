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
import re
import os
from sfvs.nvme import nvme
import sfvs.nvme_io
from sfvs.nvme.utils import Utils as utils
import filecmp
import time
import logging

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s : %(message)s')
class OCP_SMART():
    def __init__(self, ctrl, ns):
        self.ctrl = ctrl
        self.ns = ns

    def smart_OCP_vendor(self, keyword):
        status,smart_OCP_vendor_info = self.parsing_smart_OCP_vendor()
        if status != 0:
            return -1
        smart_OCP_vendor_field = smart_OCP_vendor_info[keyword]
        return smart_OCP_vendor_field

    def parsing_smart_OCP_vendor(self):
        ret = -1
        smart_OCP_vendor_all = {}
        try:
            with self.ctrl:
                # log_id:0xc0 Smart/Health Information Extended OCP smart
                ret, data = self.ctrl.log_page(0xc0, 512)
                if ret==0:
                    # The input data of log_page_print is data and log_id
                    # print(log_page_print(data.data, 0xc0))
                    smart_OCP_vendor_all["Physical_Media_Units_Written"]       = self.to_int(data[0:16])
                    smart_OCP_vendor_all["Physical_Media_Units_Read"]          = self.to_int(data[16:32])
                    smart_OCP_vendor_all["Bad_User_NAND_Blocks"]               = self.to_int(data[32:40])
                    smart_OCP_vendor_all["Bad_User_NAND_Blocks_Raw_Count"]     = self.to_int(data[32:38])
                    smart_OCP_vendor_all["Bad_User_NAND_Blocks_Normalized_Value"] = self.to_int(data[38:40])
                    smart_OCP_vendor_all["Bad_System_NAND_Blocks"]             = self.to_int(data[40:48])
                    smart_OCP_vendor_all["Bad_System_NAND_Blocks_Raw_Count"]   = self.to_int(data[40:46])
                    smart_OCP_vendor_all["Bad_System_NAND_Blocks_Normalized_Value"] = self.to_int(data[46:48])
                    smart_OCP_vendor_all["XOR_Recovery_Count"]                 = self.to_int(data[48:56])
                    smart_OCP_vendor_all["Uncorrectable_Read_Error_Count"]     = self.to_int(data[56:64])
                    smart_OCP_vendor_all["Soft_ECC_Error_Count"]               = self.to_int(data[64:72])
                    smart_OCP_vendor_all["End_to_End_Correction_Counts"]       = self.to_int(data[72:80])
                    smart_OCP_vendor_all["End_to_End_Correction_Counts_Detected_Errors"] = self.to_int(data[72:76])
                    smart_OCP_vendor_all["End_to_End_Correction_Counts_Corrected_Errors"] = self.to_int(data[76:80])
                    smart_OCP_vendor_all["System_Data_percentage_Used"]        = self.to_int(data[80:81])
                    smart_OCP_vendor_all["Refresh_Counts"]                     = self.to_int(data[81:88])
                    smart_OCP_vendor_all["User_Data_Erase_Counts"]             = self.to_int(data[88:96])
                    smart_OCP_vendor_all["User_Data_Erase_Counts_Maximum"]     = self.to_int(data[88:92])
                    smart_OCP_vendor_all["User_Data_Erase_Counts_Minimum"]     = self.to_int(data[92:96])
                    smart_OCP_vendor_all["Thermal_Throttling_Status_and_Count"]= self.to_int(data[96:98])
                    smart_OCP_vendor_all["Thermal_Throttling_Count"]           = self.to_int(data[96:97])
                    smart_OCP_vendor_all["Thermal_Throttling_Status"]          = self.to_int(data[97:98])
                    smart_OCP_vendor_all["OCP_NVMe_SSD_Specification_Version"] = self.to_int(data[98:104])
                    smart_OCP_vendor_all["PCIe_Correctable_Error_Count"]       = self.to_int(data[104:112])
                    smart_OCP_vendor_all["Incomplete_Shutdowns"]               = self.to_int(data[112:116])
                    smart_OCP_vendor_all["Reserved_1"]                         = self.to_int(data[116:120])
                    smart_OCP_vendor_all["Free_Blocks_Percentage"]             = self.to_int(data[120:121])
                    smart_OCP_vendor_all["Reserved_2"]                         = self.to_int(data[121:128])
                    smart_OCP_vendor_all["Capacitor_Health"]                   = self.to_int(data[128:130])
                    smart_OCP_vendor_all["NVMe_Errata_Version"]                = self.to_int(data[130:131])
                    smart_OCP_vendor_all["Reserved_3"]                         = self.to_int(data[131:136])
                    smart_OCP_vendor_all["Unaligned_IO"]                       = self.to_int(data[136:144])
                    smart_OCP_vendor_all["Security_Version_Number"]            = self.to_int(data[144:152])
                    smart_OCP_vendor_all["Total_NUSE"]                         = self.to_int(data[152:160])
                    smart_OCP_vendor_all["PLP_Start_Count"]                    = self.to_int(data[160:176])
                    smart_OCP_vendor_all["Endurance_Estimate"]                 = self.to_int(data[176:192])
                    smart_OCP_vendor_all["PCIe_Link_Retraining_Count"]         = self.to_int(data[192:200])
                    smart_OCP_vendor_all["Power_State_Change_Count"]           = self.to_int(data[200:208])
                    smart_OCP_vendor_all["Reserved_4"]                         = self.to_int(data[208:494])
                    smart_OCP_vendor_all["Log_Page_Version"]                   = self.to_int(data[494:496])
                    smart_OCP_vendor_all["Log_Page_GUID"]                      = self.to_int(data[496:512])
        except nvme.NVMeException as e:
            print('Error: {}'.format(str(e)))
        return ret, smart_OCP_vendor_all

    def to_int(self, data):
        return int.from_bytes(bytes(data), byteorder='little')

def find_host():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

def update_test_result(result_file, case_name, result):
    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("{}         {} \n".format(case_name, result))
        f.close()
