#
# Provides some functions for moving focus within a tiling window manager.
# Ideas and basic structure from Peter, I made it behave more consistently/
# normally, albeit with the hard assumption that our windows are perfectly
# tiled across the whole screen.
#
#	Copyright (C) 1999-2001  Peter Liljenberg <petli@ctrl-c.liu.se>
#	Copyright (C) 2011       Jacob Courtneay <jacob@sporkexec.com>
#
#	This program is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; either version 2 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


import sys
from plwm import wmanager, cfilter

class MoveFocus:
	def move_focus(self, dir):
		"""Move focus to the next pane in direction DIR."""

		if self.current_screen is None:
			return
		screen = self.current_screen
		panes = screen.panes_list

		# No panes, meaningless to try to change focus.
		if len(panes) == 0:
			return

		if screen.current_pane:
			neighbor = screen.current_pane.get_neighbor(dir)
			if neighbor is not None:
				neighbor.activate()
		else:
			# No pane is focused. Focus anything.
			panes[0].activate()

