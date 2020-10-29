#!/usr/bin/python

# Copyright (C) 2020 Lenovo.  All rights reserved.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from tacp.rest import ApiException


class ActionTimedOutException(Exception):
    pass


class InvalidActionUuidException(Exception):
    pass


class InvalidPowerActionException(Exception):
    pass


class UuidNotFoundException(Exception):
    pass


class InvalidNetworkNameException(Exception):
    pass


class InvalidNetworkTypeException(Exception):
    pass


class InvalidVnicNameException(Exception):
    pass


class InvalidFirewallOverrideNameException(Exception):
    pass


class InvalidDiskBandwidthLimitException(Exception):
    pass


class InvalidDiskIopsLimitException(Exception):
    pass


class InvalidDiskSizeException(Exception):
    pass


class InvalidDiskNameException(Exception):
    pass


class InvalidParameterException(Exception):
    pass


class CreateNetworkException(ApiException):
    pass


class AddVnicException(ApiException):
    pass
