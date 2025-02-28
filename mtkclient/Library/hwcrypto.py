#!/usr/bin/python3
# -*- coding: utf-8 -*-
# (c) B.Kerler 2018-2021 GPLv3 License
import logging
import time

from mtkclient.Library.utils import LogBase, logsetup
from mtkclient.Library.hwcrypto_gcpu import GCpu
from mtkclient.Library.hwcrypto_dxcc import dxcc
from mtkclient.Library.hwcrypto_sej import sej
from mtkclient.Library.cqdma import cqdma

class crypto_setup:
    hwcode = None
    dxcc_base = None
    gcpu_base = None
    da_payload_addr = None
    sej_base = None
    read32 = None
    write32 = None
    writemem = None
    blacklist = None
    cqdma_base = None
    ap_dma_mem = None
    meid_addr = None
    socid_addr = None
    prov_addr = None

class hwcrypto(metaclass=LogBase):
    def __init__(self, setup, loglevel=logging.INFO):
        self.__logger = logsetup(self, self.__logger, loglevel)

        self.dxcc = dxcc(setup, loglevel)
        self.gcpu = GCpu(setup, loglevel)
        self.sej = sej(setup, loglevel)
        self.cqdma = cqdma(setup, loglevel)
        self.hwcode = setup.hwcode
        self.setup = setup
        self.read32 = setup.read32
        self.write32 = setup.write32
        self.meid_addr = setup.meid_addr
        self.socid_addr = setup.socid_addr
        self.prov_addr = setup.prov_addr

    def aes_hwcrypt(self, data=b"", iv=None, encrypt=True, otp=None, mode="cbc", btype="sej"):
        if otp is None:
            otp=32*b"\00"
        else:
            if isinstance(otp,str):
                otp=bytes.fromhex(otp)
        if btype == "sej":
            if encrypt:
                if mode == "cbc":
                    return self.sej.hw_aes128_cbc_encrypt(buf=data, encrypt=True)
            else:
                if mode == "cbc":
                    return self.sej.hw_aes128_cbc_encrypt(buf=data, encrypt=False)
            if mode=="rpmb":
                return self.sej.generate_rpmb(meid=data, otp=otp)
        elif btype == "gcpu":
            addr = self.setup.da_payload_addr
            if mode == "ecb":
                return self.gcpu.aes_read_ecb(data=data, encrypt=encrypt)
            elif mode == "cbc":
                if self.gcpu.aes_setup_cbc(addr=addr, data=data, iv=iv, encrypt=encrypt):
                    return self.gcpu.aes_read_cbc(addr=addr, encrypt=encrypt)
            """
            elif mode == "mtee":
                path = "tee_tee.bin"
                with open(path,"rb") as rf:
                    rf.seek(0x240)
                    data=rf.read(0x25D3C0)
                    rf.seek(0x1C)
                    seed=rf.read(0x20)
                    self.gcpu.init()
                    self.gcpu.acquire()
                    self.gcpu.mtk_gcpu_decrypt_mtee_img(data,seed)
            """
        elif btype == "dxcc":
            if mode == "fde":
                return self.dxcc.generate_rpmb(1)
            elif mode == "rpmb2":
                return self.dxcc.generate_rpmb(2)
            elif mode == "rpmb":
                return self.dxcc.generate_rpmb()
            elif mode == "itrustee":
                return self.dxcc.generate_itrustee_fbe()
            elif mode == "prov":
                return self.dxcc.generate_provision_key()
            elif mode == "sha256":
                return self.dxcc.generate_sha256(data=data)
        else:
            self.error("Unknown aes_hwcrypt type: " + btype)
            self.error("aes_hwcrypt supported types are: sej")
            return bytearray()

    def orval(self, addr, value):
        self.write32(addr, self.read32(addr) | value)

    def andval(self, addr, value):
        self.write32(addr, self.read32(addr) & value)

    def disable_hypervisor(self):
        self.write32(0x1021a060,self.read32(0x1021a060)|0x1)

    def disable_range_blacklist(self, btype, refreshcache):
        if btype == "gcpu":
            self.info("GCPU Init Crypto Engine")
            self.gcpu.init()
            self.gcpu.acquire()
            self.gcpu.init()
            self.gcpu.acquire()
            self.info("Disable Caches")
            refreshcache(b"\xB1")
            self.info("GCPU Disable Range Blacklist")
            self.gcpu.disable_range_blacklist()
        elif btype == "cqdma":
            self.info("Disable Caches")
            refreshcache(b"\xB1")
            self.info("CQDMA Disable Range Blacklist")
            self.cqdma.disable_range_blacklist()
