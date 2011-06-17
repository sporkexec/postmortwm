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

try:
	from functools import partial # Python >= 2.5
except ImportError, e:
	def partial(fun, **kwargs):
		def wrapper(*args_called, **kwargs_called):
			kw = dict(kwargs)
			kw.update(kwargs_called)
			return fun(*args_called, **kw)
		return wrapper

class MoveFocus:
	__diff_filters = {
		# Filters to select panes in the correct general direction.
		# Chosen panes will tend to be towards upper left corner when
		# panes are staggered.
		# inputs: from_edges, to_edges
		# returns filtering bool

		# dest must be below and not to the right of current
		'down': lambda (tt, rr, bb, ll), (t, r, b, l): bb <= t and l <= ll,
		# dest must be above and not to the right of current
		'up': lambda (tt, rr, bb, ll), (t, r, b, l): b <= tt and l <= ll,
		# dest must be to the right of and not below current
		'right': lambda (tt, rr, bb, ll), (t, r, b, l): rr <= l and t <= tt,
		# dest must be to the left of and not below current
		'left': lambda (tt, rr, bb, ll), (t, r, b, l): r <= ll and t <= tt,
	}
	__diff_orders = {
		# Once filtered by direction, chooses the closest pane according to
		# upper left corner coordinates.
		# inputs: from_edges, to_edges
		# returns two numbers to be used as sorting keys, sort of like:
		# ORDER BY ret[0] ASC, ret[1] ASC LIMIT 1

		# vdiff, hdiff
		'down': lambda (tt, rr, bb, ll), (t, r, b, l): (abs(tt - t), abs(ll - l)),
		'up': lambda (tt, rr, bb, ll), (t, r, b, l): (abs(tt - t), abs(ll - l)),
		# hdiff, vdiff
		'right': lambda (tt, rr, bb, ll), (t, r, b, l): (abs(ll - l), abs(tt - t)),
		'left': lambda (tt, rr, bb, ll), (t, r, b, l): (abs(ll - l), abs(tt - t)),
	}

	def move_focus(self, dir):
		"""Move focus to the next pane in direction DIR.

		DIR is either 'up', 'down', 'left' or 'right'.
		We assume a perfectly tiled layout because it's a tiled wm...
		You may get stuck if there are holes between tiles.
		We currently do not wrap around the screen.
		"""

		if self.current_screen is None:
			return

		screen = self.current_screen
		panes = screen.panes_list

		# No panes, meaningless to try to change focus.
		if len(panes) == 0:
			return

		if screen.current_pane:
			# Find the closest pane to the currently focused pane.
			edges = screen.current_pane.get_edges()
			dfilter = partial(self.__diff_filters[dir], edges)
			dsort = partial(self.__diff_orders[dir], edges)

			best = None
			bestdiff = None

			# FIXME: Been too long since I've read the style guide, how do
			# these indentions go? Also I intentionally break the "4 spaces"
			# indention rule because it's stupid. Tabs are for indenting,
			# spaces are for tokenizing, and the argument seems to be that
			# editors make it too hard to do otherwise. Fix your fucking editor
			# and stop using 4 bytes where 1 would do. Also most editors can
			# set the width of a tab to anything so you can have 4-space tabs,
			# 2-space tabs, or even 8-space tabs without changing the file.
			# Seems much more straightforward than making a kludge to translate
			# a tab key into x many spaces on disk and a delete key on a tab
			# boundary to x many characters deleted. /rant
			for p in panes:
				p_edges = p.get_edges()
				if p is screen.current_pane or not dfilter(p_edges):
					continue

				p_diff = dsort(p_edges)
				if (bestdiff is None or p_diff[0] < bestdiff[0] or
						(p_diff[0] == bestdiff[0] and p_diff[1] < bestdiff[1])):
					best = p
					bestdiff = p_diff

			if best is not None:
				best.activate()

		else:
			# No pane is focused. Focus anything.
			panes[0].activate()

