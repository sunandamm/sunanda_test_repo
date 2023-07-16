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
import subprocess
import socket
import pytest
import logging
import paramiko
import time
from paramiko.ssh_exception import NoValidConnectionsError
from paramiko.ssh_exception import AuthenticationException

def powercycle_device(pi_info):
    logging.info("Start to power cycle the device !")
    logging.info("pi_info = {}".format(pi_info))
    logging.info(type(pi_info))

    pi_ip = pi_info.split(";")[0].strip()
    path = pi_info.split(";")[1].strip()
    board = pi_info.split(";")[2].strip()
    logging.info("pi_ip = {}".format(pi_ip))
    logging.info("path = {}".format(path))
    logging.info("board = {}".format(board))

    if "e1.s" in board:
        cmd = "cd "+ path +" ; sudo python lib/util/spi_boot_mode_e1s.py"  # E1.S
    else:
        cmd = "cd "+ path +" ; sudo python lib/util/spi_boot_mode.py"      # EVB
    pi_name = 'pi'
    password = '123456'

    try:
        logging.info("Remove all drive PCIe device")
        time.sleep(3)
        remove_all_pcie()

        logging.info("Power cycle the device")
        time.sleep(3)
        ssh_cmd(pi_ip, pi_name, cmd, password)

        logging.info("Rescan drive PCIe device")
        time.sleep(3)
        device_rescan()
        time.sleep(1)
        logging.info("Power cycle the device Finished !")
    except:
        logging.error("Power cycle failed")

def power_loss_device(pi_info):
    logging.info("Start to power loss the device !")
    pi_ip = pi_info.split(";")[0].strip()
    path = pi_info.split(";")[1].strip()
    board = pi_info.split(";")[2].strip()
    if "e1.s" in board:
        cmd = "cd "+ path +" ; sudo python lib/util/spi_boot_mode_e1s.py"  # E1.S
    else:
        cmd = "cd "+ path +" ; sudo python lib/util/spi_boot_mode.py"      # EVB
    pi_name = 'pi'
    password = '123456'
    try:
        logging.info("Power Loss the device")
        time.sleep(3)
        ssh_cmd(pi_ip, pi_name, cmd, password)
        logging.info("SSH command completed")

        logging.info("Remove all drive PCIe device")
        time.sleep(30)
        remove_all_pcie()

        logging.info("Rescan drive PCIe device")
        time.sleep(3)
        device_rescan()
        time.sleep(1)
        logging.info("Power Loss the device Finished !")
    except:
        logging.error("Power Loss failed")

def ssh_cmd(pi_ip, pi_name, cmd, password):
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname=pi_ip, port=22, username=pi_name, password='123456', allow_agent=False, look_for_keys=False)
        conn = ssh.invoke_shell()# to keep the session go on
        conn.keep_this = ssh

        time.sleep(1)
        conn.send("terminal length 0\n")
        time.sleep(1)

        if conn.recv_ready():
            conn.recv(65535)
        logging.info(conn)
        flag = 0 
        try:
            logging.info("execute ssh cmd is:")
            logging.info(cmd)
            stdin, stdout, stderr = ssh.exec_command(cmd, get_pty = True)
            stdin.write(password + "\n")
            stdin.flush()
            for line in iter(stdout.readline,'b'): 
                logging.info(line) 
                if not line:
                    break
                if ("wait 10 sec for hot plug" in line or 'Please hot-plug the disk.' in line) and flag != 1:
                    logging.info("do power cycle")
                    flag = 1
                    #umst_syscommon.mp_nvme_download_mode()
                    logging.info("delay 50 sec")
                    time.sleep(50)
            result = stderr.read()
            if result:
                logging.info(str(result,encoding='utf-8'))
                pytest.fail("ssh cmd execute fail")
            else:
                logging.info("ssh success")
        except Exception as e:
            pytest.fail("ssh cmd failed, which is {}".format(e))
    except NoValidConnectionsError as e:
        pytest.fail("ssh connect failed, which is {}".format(e))
    except AuthenticationException as t:
        pytest.fail("ssh password is error, which is {}".format(t))
    except socket.timeout as e:
        pytest.fail("socket is timeout and ssh cmd failed, which is {}".format(e))
    finally:
        ssh.close()

def remove_all_pcie():
    pcie_addr_list = get_pcie_addr()
    logging.info("pcie_addr_list length = {}".format(len(pcie_addr_list)))
    i = len(pcie_addr_list)
    while i > 0:
        pci_number = "0000:" + pcie_addr_list[i - 1]
        logging.debug(pci_number)
        cd_mode_pci_device_remove = "sudo chmod 777 /sys/bus/pci/devices/" + pci_number + "/remove"
        remove_pci_device = "sudo echo 1 >/sys/bus/pci/devices/" + pci_number + "/remove"
        logging.info("remove_pci_device = {}".format(remove_pci_device))
        time.sleep(0.5)
        os.system(cd_mode_pci_device_remove)
        time.sleep(0.5)
        os.system(remove_pci_device)
        i = i - 1

def get_pcie_addr():
    '''
    Get pcie address from "lspci" command
    '''
    pcie_addr_list = []
    cmd = "lspci | grep Non-Volatile"
    ret, out = execute_cmd(cmd, 10, out_flag = True)
    if out == []:
        logging.error("No device found")
    else:
        for item in out:
            pcie_addr = item.split(" ")[0].strip()
            pcie_addr_list.append(pcie_addr)
        logging.info("pcie_addr list: {}".format(pcie_addr_list))
    return pcie_addr_list

def execute_cmd(cmd, timeout, out_flag = False, expect_fail = False, expect_err_info = None):
    '''
	# Execute cmd in #timeout seconds
	# out_flag: True means return cmd out(a str list), False not.
	# expect_fail: for some error inject scenario, set this to True
	# expect_err_info: if expect failure, then check the error msg as expected or not
    '''
    logging.info(cmd)
    result = 0
    out = []
    try:
        p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell = True) 
        t_beginning = time.time()
        seconds_passed = 0 
        while True:
            if p.poll() is not None: 
                out = p.stdout.readlines()
                out = [i.decode().strip("\n") for i in out]  # convert to string
                if p.returncode == 0:
                    logging.info("Cmd executed successfully")
                elif p.returncode != 1:  # specified scenario: nvme list | grep nvme, if nothing returned, the returncode is 1, it seems caused by the grep, for ex. ls | grep leon, if nothing found, returncode is 1
                    logging.info("Cmd output: {}".format(out[0]))  # just show the first out to avoid too many logs
                    if expect_fail:
                        logging.info("Cmd executed failed, but it's as expected")
                        result = 0
                        if expect_err_info != None and expect_err_info not in out[0]:
                            logging.warning("Error msg not as expected, you may have a check")
                    else:
                        logging.info("Cmd executed failed")
                        result = -1
                break 
            time.sleep(1)
            seconds_passed = time.time() - t_beginning 
            if seconds_passed > timeout: 
                p.stdout.close()
                p.terminate()
                logging.info('Cmd not end as expected in {} seconds, terminate it'.format(timeout))
                result = -2
                return result, out
                # break
        p.stdout.close()
    except Exception as e:
        logging.error("Cmd execution failed: {}".format(e))
        result = -1, out
    if out_flag == False:
        return result
    else:
        return result, out

def device_rescan():
    logging.info("NVMe rescan")
    cmd1 = 'sudo chmod 777 /sys/bus/pci/rescan'
    cmd2 = 'sudo echo 1 > /sys/bus/pci/rescan'
    time.sleep(2)
    os.system(cmd1)
    time.sleep(2)
    os.system(cmd2)
    time.sleep(2)
    cmd4 =  'sudo ls /dev/ | grep nvme* '
    os.system(cmd4)
    result = 0
    return result

def run_fio_param(offset, rw, bs, Qdepth, pattern, size, runtime="0", verify="0"):
    cmd,fio_log = generate_io_cmd(offset, rw, bs, Qdepth, pattern, size, runtime=runtime, verify=verify)
    logging.info(cmd)
    run_fio(runtime,cmd)
    test_flag = fio_verify(fio_log)
    return test_flag

def generate_io_cmd(offset, rw, bs, Qdepth, pattern, size, runtime="0", verify="0"):
    '''
    param
    rw: read, write, randread, randwrite, randread_unaligned
    bs: 4k, 8k, 32k, 64k, 128k
    Qdepth: 1,8, 16, 32, 64
    size: range size
    runtime: s
    return: fio result
    '''
    if runtime != "0":
        time_based = " --time_based --runtime={}".format(runtime)
    else:
        time_based = ""
    if verify == "1":
        verify_cmd = " --do_verify=1 --verify_dump=1 --verify_fatal=1 --verify_backlog=1"
    else:
        verify_cmd = " --do_verify=0"
    fio_log = "fio_" + rw + ".log"

    if rw == "randread_unaligned":
        cmd = "sudo fio --name={} --offset={} --ioengine=libaio --direct=1 --buffered=0 --size={} --continue_on_error=0 --bs={}--iodepth={} --verify_pattern=0x{} --verify=meta --rw=randread --filename=/dev/nvme0n1 --output={}{}{}".format(rw, offset, size, bs, Qdepth, pattern, fio_log, time_based, verify_cmd)
    elif rw == "write_unaligned":
        cmd = "sudo fio --name={} --offset={} --ioengine=libaio --direct=1 --buffered=0 --size={} --continue_on_error=0 --bs={} --iodepth={} --verify_pattern=0x{} --verify=meta --rw=write --filename=/dev/nvme0n1 --output={}{}{}".format(rw, offset, size, bs, Qdepth, pattern, fio_log, time_based, verify_cmd)
    else:
        cmd = "sudo fio --name={} --offset={} --ioengine=libaio --direct=1 --buffered=0 --size={} --continue_on_error=0 --bs={} --iodepth={} --verify_pattern=0x{} --verify=meta --rw={} --filename=/dev/nvme0n1 --output={}{}{}".format(rw, offset, size, bs, Qdepth, pattern, rw, fio_log, time_based, verify_cmd)
    return cmd,fio_log

def run_fio(runtime,cmd):
    p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    t_beginning = time.time()
    result = -1
    timeout = 30
    while True:
        if p.poll() is not None:
            logging.info(" FIO test is done.")
            break
        time.sleep(5)
        seconds_passed = time.time() - t_beginning
        if seconds_passed > int(timeout) + int(runtime):
            p.terminate()
            logging.error("check write unaligned result fail")

def fio_verify(fio_log):
    flag = -1
    with open(fio_log, 'r') as processLog:
        while True:
            entry = processLog.readline()
            if "err=" in entry:
                if "err= 0" in entry:
                    result = 0
                    logging.info(entry.strip())
                    logging.info(" Check FIO: pass")
                    flag = 0
                    break
                else:
                    logging.info(" Check FIO: fail")
                    break
            elif entry == '':
                break
    return flag
