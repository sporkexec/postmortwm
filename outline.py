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


from Xlib import X
from plwm import wmanager
from panes import Pane

# FIXME: Do this (inheritance et al) right once you've got your head wrapped around it.
# TODO MAYBE: Outlines are actually drawn within the pane, ie obscuring windows. Is this bad?
class OutlinePane(Pane):
	"""Draws a border around (within, rather) a pane.

	We use four small windows to draw the edges of the border. Reparenting or
	using normal border won't work because we won't always have a window to
	draw around; we only deal with panes.
	"""
	border_width = 1

	def __init__(self, *args):
		self.outline_windows = None
		Pane.__init__(self, *args)

	def activate(self):
		Pane.activate(self)
		self.outline_show()

	def deactivate(self):
		self.outline_hide()
		Pane.deactivate(self)

	def horizontal_split(self, *args):
		Pane.horizontal_split(self, *args)
		self.outline_show()

	def vertical_split(self, *args):
		Pane.vertical_split(self, *args)
		self.outline_show()

	def outline_show(self):
		self.outline_hide()
		self.outline_windows = []

		# Grab 4 windows with no border, white background.
		# TODO: Figure out how to do more colors.
		for _ in range(4):
			self.outline_windows.append(self.screen.root.create_window(
				0, 0, 1, 1, 0, X.CopyFromParent,
				background_pixel = self.screen.info.white_pixel,
				save_under = 1
				))

		bw = self.border_width
		edges = self.get_edges()
		width = edges[1] - edges[3]
		height = edges[2] - edges[0]

		# Resize windows.
		self.outline_windows[0].configure(x = edges[3], y = edges[0], width = width, height = bw) #t
		self.outline_windows[1].configure(x = edges[1] - bw, y = edges[0], width = bw, height = height) #r
		self.outline_windows[2].configure(x = edges[3], y = edges[2] - bw, width = width, height = bw) #b
		self.outline_windows[3].configure(x = edges[3], y = edges[0], width = bw, height = height) #l

		for w in self.outline_windows:
			w.configure(stack_mode = X.Above)
			w.map()

	def outline_hide(self):
		if self.outline_windows is None:
			return
		for w in self.outline_windows:
			w.destroy()
		self.outline_windows = None

