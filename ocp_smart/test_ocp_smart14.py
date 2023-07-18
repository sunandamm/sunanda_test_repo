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
from sfvs.nvme import nvme
import argparse
import ctypes
import pytest
import os
import numpy as np
import shutil
from enum import IntEnum
from struct import *
from base_func import cGSD_func
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')

# Adding the VSC info 

OUTPUTDIR           = "outs"
WORKSPACE           = os.getcwd()
DEFAULT_OUTPUT_DIR  = os.path.join(WORKSPACE, OUTPUTDIR)
TEMP_OUTPUT_DIR     = os.path.join(WORKSPACE, "temp")

# VSC basic command constant
cCmdPacketBufferSizeInByte  = 512
cSetupVscCommand            = 0xFC  # Setup the VSC command, From host to device only.
cExecuteVscCommand          = 0xFD  # Execute the VSC command that has been setup.

# D2H buffer size
cMaxD2HBuffSizeInByte         = 256 * 1024
np.set_printoptions(threshold=np.inf)
SSH_CMD = "sudo sshpass -p 123456 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
TESTBED_PATH = "/home/fte/FTE/USECASE/Vega_CI_Script/TestBed"
write_file = 'write_test' + '.bin'
read_file = 'read_test' + '.bin'
M8_NUM = 8
M7_NUM=2

# VSC basic command constant
cCmdPacketBufferSizeInByte  = 512
cSetupVscCommand            = 0xFC  # Setup the VSC command, From host to device only.
cExecuteVscCommand          = 0xFD  # Execute the VSC command that has been setup.

class HostXferDirection_t(IntEnum):
    '''
    typedef enum HostXferDirection_t
    {
        cXferD2h=0,                                         ///< Device to host transfer (Host read, data in)
        cXferH2d=1,                                         ///< Host to device transfer (Host write, data out)
        cXferNone=2                                         ///< No data transfer
    } HostXferDirection_t;
    '''
    cXferH2D = 0xFD
    cXferD2H = 0xFE
    cXferNone = 0xFC
	

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

	
    # -----------------------------------------------------------------------------------------------------------
    # Functionality API VSC
    # -----------------------------------------------------------------------------------------------------------
    def SendSetupVscCommand(self, bufferFile, dataLength=cCmdPacketBufferSizeInByte, hostXfer=HostXferDirection_t.cXferH2D, timeoutInMs=7000):
        '''
        example: H2D, size = 512B (0x80 DW), subOpcode in binary file
        cat hex.txt | xxd -r -p > file
        sudo nvme admin-passthru /dev/nvme0n1 --opcode=0xFD --data-len=512 -w --cdw12=0xFC --cdw10=0x80 --cdw15=0x1 -i file -s
        '''
        dataSizeInDWord = int(dataLength / 4)
        #print("SendSetupVscCommand: CDW 0: {:X}, CDW10: {:X}, CDW12: {:X}".format(hostXfer, dataSizeInDWord, cSetupVscCommand))

        # sudo nvme admin-passthru /dev/nvme0n1 --opcode=0xFD --data-len=512 -w --cdw12=0xFC --cdw10=0x80 -i file -s
        nvmeCliCmd    = "sudo nvme admin-passthru"
        commandStrFmt = "{cmd} /dev/nvme0n1 --opcode=0x{op:X} --data-len={len} -w --cdw10=0x{CDW10:X} --cdw12=0x{CDW12:X} --timeout={to:d} -i {file}"

        rc, out, err = self.RunCommand(commandStrFmt.format(cmd=nvmeCliCmd, op=hostXfer, len=dataLength, CDW10=dataSizeInDWord, CDW12=cSetupVscCommand, to=timeoutInMs, file=bufferFile), dryRun=False)
        if rc != 0:
            print("      | Retrieve info cmdPacket(FC) rc: {}, out=({}), err=({})".format(rc, out, err))
        return (rc == 0)

    def SendExecuteVscCommand(self, bufferFile, dataLength, hostXfer=HostXferDirection_t.cXferNone, timeoutInMs=7000):
        '''
        example: D2H, size = 256KB (0x10000 DW), subOpcode in binary file
        sudo nvme admin-passthru /dev/nvme0n1 --opcode=0xFE --data-len=262144 -r --cdw12=0xFD --cdw10=0x10000 --cdw15=0x1 -i file -b > raw1.dat
        '''
        dataSizeInDWord     = int(dataLength / 4)
        #print("Execute packet: CDW 0: {:X}, CDW10: {:X}, CDW12: {:X}".format(hostXfer, dataSizeInDWord, cExecuteVscCommand))

        nvmeCliCmd    = "sudo nvme admin-passthru"
        if hostXfer == HostXferDirection_t.cXferD2H:
            commandStrFmt = "{cmd} /dev/nvme0n1 --opcode=0x{op:X} --data-len={len} -r --cdw10=0x{CDW10:X} --cdw12=0x{CDW12:X} --timeout={to:d} -b > {file}"
        elif hostXfer == HostXferDirection_t.cXferH2D:
            commandStrFmt = "{cmd} /dev/nvme0n1 --opcode=0x{op:X} --data-len={len} -w --cdw10=0x{CDW10:X} --cdw12=0x{CDW12:X} --timeout={to:d} -i {file}"
        else:
            commandStrFmt = "{cmd} /dev/nvme0n1 --opcode=0x{op:X} --cdw12=0x{CDW12:X} -i {file}"    


        rc, out, err = self.RunCommand(commandStrFmt.format(cmd=nvmeCliCmd, op=hostXfer, len=dataLength, CDW10=dataSizeInDWord, CDW12=cExecuteVscCommand, to=timeoutInMs, file=bufferFile), dryRun=False)
        if rc != 0:
            print("      | Retrieve info ExePacket(FD) rc: {}, out=({}), err=({})".format(rc, out, err))
        return (rc == 0)	
		
		
	
# SMART-15
# SMART-16
# SMART-17
# SMART-17

def test_NVMeSmart_OCP_Incomplete_Shutdowns(pi_info):
    case_name = "SMART-15  NVMeSmart_OCP_Incomplete_Shutdowns"
    logging.info(case_name+"\n")
    global host,ctrl, ns, hostname, folder_name
    result_file = folder_name
    result = "FAILED"
    # result = "Need_FW_Support_PLP"
   # pi_ip = pi_info.split(";")[0].strip()
    #if pi_ip == "0.0.0.0":
     #   result = "FAILED_Need_Pi_To_Powerloss"
      #  ocp_smart_lib.update_test_result(result_file, case_name, result)
       # pytest.skip("This case need the pi to control the power module")
    #ctrl.close()
    #ns.close()
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

     #   p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
      #  time.sleep(3)
      #  sys_lib.power_loss_device(pi_info)

       # logging.info("wait FW update the smart info: 60s")
       # time.sleep(75)
        #logging.info("Sherlock Find the device")

#### Adding the core dump function 
		def TriggerCoreAssert(self, core_idx):
        try:
            # Data buffer
            print("TriggerCoreAssert")
            subOpCode           = 0x0034
            assert_num          = 0x04     
            cmdPacketBuffer = bytearray(cCmdPacketBufferSizeInByte)
            cmdPacketBuffer[0:2]  = subOpCode.to_bytes(2, byteorder="little")
            cmdPacketBuffer[2]  = int(core_idx)
            cmdPacketBuffer[3]  = assert_num
            self.WriteDataListToBinaryFile("cdb_file", cmdPacketBuffer, isByteArray=True)
            # print(cmdPacketBuffer[0:16])
            # Send command packet (0xFC), H2D (0xFD)
            if self.SendSetupVscCommand("cdb_file"):
                outputBufferFile    = "output_file"
                if self.SendExecuteVscCommand(outputBufferFile, cMaxD2HBuffSizeInByte, HostXferDirection_t.cXferNone):
                    # Got a snippet of the RSL, start to combine
                    print("send trigger core dump assert cmd success")
            else:
                print("Got error after sending vsc (FD) while TriggerCoreAssert")
        except Exception as e:
            print('TriggerCoreAssert failed: {}'.format(e))

        
		#host = nvme.Host.enumerate()[0]
        #ctrl = host.controller.enumerate()[0]
        #ns = ctrl.enumerate_namespace()[0]
        #ctrl.open()
        #ns.open()
        #smart = OCP_SMART(ctrl, ns)
        
		# Get the Incomplete_Shutdowns from Smart after Power Loss
        Icomplete_Shutdowns_after=int(smart.smart_OCP_vendor("Incomplete_Shutdowns"))
        logging.info("Incomplete_Shutdowns after Incomplete Shutdowns  =   {}".format(Incomplete_Shutdowns_after))
        if Incomplete_Shutdowns_after > Incomplete_Shutdowns_before:
            result = "Pass"
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        ocp_smart_lib.update_test_result(result_file, case_name, result)
    if result == "FAILED":
        pytest.fail("NVMeSmart_OCP_Incomplete_Shutdowns Fail")

