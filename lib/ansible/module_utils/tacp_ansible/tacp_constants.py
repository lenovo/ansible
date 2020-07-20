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

class ApiState:
    RUNNING = "Running"
    SHUTDOWN = "Shut down"
    PAUSED = "Paused"
    RESTARTING = "Restarting"
    RESUMING = "Resuming"
    CREATING = "Creating"
    DELETING = "Deleting"


class PlaybookState:
    STARTED = "started"
    SHUTDOWN = "shutdown"
    STOPPED = "stopped"
    RESTARTED = "restarted"
    FORCE_RESTARTED = "force-restarted"
    PAUSED = "paused"
    ABSENT = "absent"
    RESUMED = "resumed"

    @classmethod
    def _all(cls):
        return [getattr(cls, attr) for attr in dir(cls)
                if not attr.startswith('_')]
