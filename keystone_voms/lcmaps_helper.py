# Copyright 2014 Spanish National Research Council
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ctypes
import os
import pwd


class _account_info(ctypes.Structure):
    # enolfc: assumes uid/gid are uint
    _fields_ = [
        ('uid', ctypes.c_uint),
        ('pgid_list',  ctypes.POINTER(ctypes.c_uint)),
        ('npgid', ctypes.c_int32),
        ('sgid_list', ctypes.POINTER(ctypes.c_uint)),
        ('nsgid', ctypes.c_int32),
        ('poolindex', ctypes.c_char_p),
    ]


class LCMAPSError(Exception):
    pass


class LCMAPS(object):
    """Context Manager for LCMAPS handling"""

    def __init__(self, lcmaps_lib, lcmaps_db_file=None,
                 lcmaps_debug_level=None):
        self.LCMAPSApi = ctypes.CDLL(lcmaps_lib, mode=ctypes.RTLD_GLOBAL)

        self.lcmaps_db_file = lcmaps_db_file
        self.lcmaps_debug_level = lcmaps_debug_level
        self.account_info = _account_info()

    def __enter__(self):
        # XXX: log file?
        if self.lcmaps_db_file:
            os.environ['LCMAPS_DB_FILE'] = self.lcmaps_db_file
        if self.lcmaps_debug_level:
            os.environ['LCMAPS_DEBUG_LEVEL'] = str(self.lcmaps_debug_level)
        rc = self.LCMAPSApi.lcmaps_init(0)
        if rc != 0:
            raise LCMAPSError("Unable to initialize LCMAPS library")
        rc = self.LCMAPSApi.lcmaps_account_info_init(
            ctypes.byref(self.account_info))
        if rc != 0:
            raise LCMAPSError("Error creating LCMAPS account info")
        return self

    def retrieve(self, cert_pem):
        rc = self.LCMAPSApi.lcmaps_return_account_from_pem(
            cert_pem, -1, ctypes.byref(self.account_info))
        if rc != 0:
            return {}
        username = pwd.getpwuid(self.account_info.uid).pw_name
        # TODO: use this information?
        pgids = [self.account_info.pgid_list[i]
                 for i in xrange(self.account_info.npgid)]
        sgids = [self.account_info.sgid_list[i]
                 for i in xrange(self.account_info.nsgid)]
        return {
            'user': username,
        }

    def __exit__(self, type, value, tb):
        rc = self.LCMAPSApi.lcmaps_account_info_clean(
            ctypes.byref(self.account_info))
        if rc != 0:
            raise LCMAPSError("Error freeing LCMAPS account info")
        rc = self.LCMAPSApi.lcmaps_term()
        if rc != 0:
            raise LCMAPSError("Unable to terminate LCMAPS library")
